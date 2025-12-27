use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

use crate::model::{ModelType, TrainingConfig, InferenceConfig, ValidationConfig};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub selected_model: Option<ModelType>,
    pub recent_configs: Vec<String>,
    pub theme: Theme,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum Theme {
    Dark,
    Light,
    HighContrast,
}

impl Default for Theme {
    fn default() -> Self {
        Theme::Dark
    }
}

impl Default for AppConfig {
    fn default() -> Self {
        AppConfig {
            selected_model: None,
            recent_configs: vec![],
            theme: Theme::default(),
        }
    }
}

pub struct ConfigManager {
    config_path: String,
}

impl ConfigManager {
    pub fn new(config_path: &str) -> Self {
        ConfigManager {
            config_path: config_path.to_string(),
        }
    }

    pub fn load_config(&self) -> Result<AppConfig> {
        let path = Path::new(&self.config_path);
        if !path.exists() {
            return Ok(AppConfig::default());
        }

        let content = fs::read_to_string(&path)
            .context("Failed to read config file")?;
        
        serde_yaml::from_str(&content)
            .context("Failed to parse config file")
    }

    pub fn save_config(&self, config: &AppConfig) -> Result<()> {
        let path = Path::new(&self.config_path);
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .context("Failed to create config directory")?;
        }

        let content = serde_yaml::to_string(config)
            .context("Failed to serialize config")?;
        
        fs::write(&path, content)
            .context("Failed to write config file")?;

        Ok(())
    }

    pub fn load_training_config(&self, path: &str) -> Result<TrainingConfig> {
        let content = fs::read_to_string(path)
            .context("Failed to read training config")?;
        
        serde_yaml::from_str(&content)
            .context("Failed to parse training config")
    }

    pub fn save_training_config(&self, path: &str, config: &TrainingConfig) -> Result<()> {
        let content = serde_yaml::to_string(config)
            .context("Failed to serialize training config")?;
        
        fs::write(path, content)
            .context("Failed to write training config")?;

        Ok(())
    }

    pub fn list_configs(&self, configs_dir: &str) -> Result<Vec<String>> {
        let path = Path::new(configs_dir);
        if !path.exists() {
            return Ok(vec![]);
        }

        let mut configs = vec![];
        for entry in fs::read_dir(path)
            .context("Failed to read configs directory")?
        {
            let entry = entry.context("Failed to read directory entry")?;
            let file_path = entry.path();
            
            if file_path.extension().map_or(false, |ext| ext == "yaml" || ext == "yml") {
                if let Some(name) = file_path.file_name() {
                    configs.push(name.to_string_lossy().to_string());
                }
            }
        }

        configs.sort();
        Ok(configs)
    }
}
