use anyhow::{Context, Result};
use tokio::process::Command;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::sync::mpsc;

use crate::model::{TrainingConfig, TrainingProgress};

pub struct TrainingManager {
    process: Option<tokio::process::Child>,
}

impl TrainingManager {
    pub fn new() -> Self {
        TrainingManager {
            process: None,
        }
    }

    pub async fn start_training(
        &mut self,
        config: &TrainingConfig,
        progress_tx: mpsc::UnboundedSender<TrainingProgress>,
    ) -> Result<()> {
        let mut cmd = Command::new("python");
        cmd.arg("train.py")
            .arg("--model_type")
            .arg(config.model_type.key())
            .arg("--config_path")
            .arg(&config.config_path)
            .arg("--results_path")
            .arg(&config.results_path);

        if let Some(checkpoint) = &config.start_checkpoint {
            cmd.arg("--start_check_point").arg(checkpoint);
        }

        for data_path in &config.data_paths {
            cmd.arg("--data_path").arg(data_path);
        }

        if let Some(valid_path) = &config.valid_path {
            cmd.arg("--valid_path").arg(valid_path);
        }

        if let Some(num_workers) = config.num_workers {
            cmd.arg("--num_workers").arg(num_workers.to_string());
        }

        if let Some(device_ids) = &config.device_ids {
            let devices: Vec<String> = device_ids.iter().map(|id| id.to_string()).collect();
            cmd.arg("--device_ids").arg(devices.join(","));
        }

        let mut child = cmd.spawn()
            .context("Failed to spawn training process")?;

        let stdout = child.stdout.take().context("Failed to capture stdout")?;
        let stderr = child.stderr.take().context("Failed to capture stderr")?;

        let stdout_reader = BufReader::new(stdout);
        let mut stderr_reader = BufReader::new(stderr);

        let progress_tx_clone = progress_tx.clone();
        let stdout_task = tokio::spawn(async move {
            let mut lines = stdout_reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                if let Some(parsed) = parse_training_output(&line) {
                    let _ = progress_tx_clone.send(parsed);
                }
            }
        });

        let stderr_task = tokio::spawn(async move {
            let mut lines = stderr_reader.lines();
            while let Ok(Some(line)) = lines.next_line().await {
                eprintln!("Training error: {}", line);
            }
        });

        self.process = Some(child);

        stdout_task.await.context("stdout task failed")?;
        stderr_task.await.context("stderr task failed")?;

        Ok(())
    }

    pub async fn stop_training(&mut self) -> Result<()> {
        if let Some(mut child) = self.process.take() {
            child.kill().await.context("Failed to stop training process")?;
        }
        Ok(())
    }

    pub fn is_running(&self) -> bool {
        self.process.is_some()
    }
}

fn parse_training_output(line: &str) -> Option<TrainingProgress> {
    if line.contains("epoch:") {
        let epoch_str = line.split("epoch:").nth(1)?
            .trim()
            .split_whitespace()
            .next()?;
        let epoch: usize = epoch_str.parse().ok()?;

        return Some(TrainingProgress {
            epoch,
            train_loss: 0.0,
            valid_loss: None,
            sdr: None,
            sir: None,
            sar: None,
            isr: None,
            gpu_memory: None,
            gpu_utilization: None,
        });
    }

    if line.contains("SDR:") {
        let sdr_str = line.split("SDR:").nth(1)?
            .trim()
            .split_whitespace()
            .next()?;
        let sdr: f64 = sdr_str.parse().ok()?;

        return Some(TrainingProgress {
            epoch: 0,
            train_loss: 0.0,
            valid_loss: None,
            sdr: Some(sdr),
            sir: None,
            sar: None,
            isr: None,
            gpu_memory: None,
            gpu_utilization: None,
        });
    }

    None
}
