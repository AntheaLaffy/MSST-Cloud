use anyhow::{Context, Result};
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader};

use crate::model::{InferenceConfig, InferenceResult};

pub struct InferenceManager {
    process: Option<tokio::process::Child>,
}

impl InferenceManager {
    pub fn new() -> Self {
        InferenceManager {
            process: None,
        }
    }

    pub async fn run_inference(
        &mut self,
        config: &InferenceConfig,
    ) -> Result<InferenceResult> {
        let mut cmd = Command::new("python");
        cmd.arg("inference.py")
            .arg("--model_type")
            .arg(config.model_type.key())
            .arg("--config_path")
            .arg(&config.config_path)
            .arg("--start_check_point")
            .arg(&config.start_checkpoint)
            .arg("--input_folder")
            .arg(&config.input_folder)
            .arg("--store_dir")
            .arg(&config.store_dir);

        let mut child = cmd.spawn()
            .context("Failed to spawn inference process")?;

        let stdout = child.stdout.take().context("Failed to capture stdout")?;
        let stderr = child.stderr.take().context("Failed to capture stderr")?;

        let stdout_reader = BufReader::new(stdout);
        let stderr_reader = BufReader::new(stderr);

        let stderr_task = tokio::spawn(async move {
            let mut lines = stderr_reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                eprintln!("Inference error: {}", line);
            }
        });

        let stdout_task = tokio::spawn(async move {
            let mut lines = stdout_reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                println!("{}", line);
            }
        });

        let status = child.wait().await.context("Failed to wait for inference process")?;

        stdout_task.await.context("stdout task failed")?;
        stderr_task.await.context("stderr task failed")?;

        if status.success() {
            Ok(InferenceResult {
                input_file: config.input_folder.clone(),
                output_dir: config.store_dir.clone(),
                duration: None,
                success: true,
                error_message: None,
            })
        } else {
            Ok(InferenceResult {
                input_file: config.input_folder.clone(),
                output_dir: config.store_dir.clone(),
                duration: None,
                success: false,
                error_message: Some(format!("Process exited with code: {}", status.code().unwrap_or(-1))),
            })
        }
    }

    pub async fn stop_inference(&mut self) -> Result<()> {
        if let Some(mut child) = self.process.take() {
            child.kill().await.context("Failed to stop inference process")?;
        }
        Ok(())
    }

    pub fn is_running(&self) -> bool {
        self.process.is_some()
    }
}
