use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ModelType {
    MDX23C,
    HtDemucs,
    VitLarge23,
    TorchSeg,
    BsRoformer,
    MelBandRoformer,
    SwinUpernet,
    BandIt,
    ScNet,
    BandItV2,
    Apollo,
    TsBsMamba2,
    Conformer,
    BsConformer,
    ScNetTran,
    ScNetMasked,
}

impl ModelType {
    pub fn key(&self) -> &'static str {
        match self {
            ModelType::MDX23C => "mdx23c",
            ModelType::HtDemucs => "htdemucs",
            ModelType::VitLarge23 => "segm_models",
            ModelType::TorchSeg => "torchseg",
            ModelType::BsRoformer => "bs_roformer",
            ModelType::MelBandRoformer => "mel_band_roformer",
            ModelType::SwinUpernet => "swin_upernet",
            ModelType::BandIt => "bandit",
            ModelType::ScNet => "scnet",
            ModelType::BandItV2 => "bandit_v2",
            ModelType::Apollo => "apollo",
            ModelType::TsBsMamba2 => "bs_mamba2",
            ModelType::Conformer => "conformer",
            ModelType::BsConformer => "bs_conformer",
            ModelType::ScNetTran => "scnet_tran",
            ModelType::ScNetMasked => "scnet_masked",
        }
    }

    pub fn name(&self) -> &'static str {
        match self {
            ModelType::MDX23C => "MDX23C",
            ModelType::HtDemucs => "Demucs4HT",
            ModelType::VitLarge23 => "VitLarge23",
            ModelType::TorchSeg => "TorchSeg",
            ModelType::BsRoformer => "Band Split RoFormer",
            ModelType::MelBandRoformer => "Mel-Band RoFormer",
            ModelType::SwinUpernet => "Swin Upernet",
            ModelType::BandIt => "BandIt Plus",
            ModelType::ScNet => "SCNet",
            ModelType::BandItV2 => "BandIt v2",
            ModelType::Apollo => "Apollo",
            ModelType::TsBsMamba2 => "TS BSMamba2",
            ModelType::Conformer => "Conformer",
            ModelType::BsConformer => "BS Conformer",
            ModelType::ScNetTran => "SCNet Tran",
            ModelType::ScNetMasked => "SCNet Masked",
        }
    }

    pub fn description(&self) -> &'static str {
        match self {
            ModelType::MDX23C => "KUIELab TFC TDF v3 architecture",
            ModelType::HtDemucs => "Hybrid transformer architecture",
            ModelType::VitLarge23 => "Vision transformer based",
            ModelType::TorchSeg => "Segmentation models with 800+ encoders",
            ModelType::BsRoformer => "Rotary attention with band splitting",
            ModelType::MelBandRoformer => "Mel-spectrogram band splitting",
            ModelType::SwinUpernet => "Swin transformer with UperNet",
            ModelType::BandIt => "Band-limited attention",
            ModelType::ScNet => "Spectral convolution network",
            ModelType::BandItV2 => "Improved band-limited attention",
            ModelType::Apollo => "Advanced separation architecture",
            ModelType::TsBsMamba2 => "State space model",
            ModelType::Conformer => "Convolution-augmented transformer",
            ModelType::BsConformer => "Band split conformer",
            ModelType::ScNetTran => "Transformer variant",
            ModelType::ScNetMasked => "Masked variant",
        }
    }

    pub fn all_models() -> Vec<ModelType> {
        vec![
            ModelType::MDX23C,
            ModelType::HtDemucs,
            ModelType::VitLarge23,
            ModelType::TorchSeg,
            ModelType::BsRoformer,
            ModelType::MelBandRoformer,
            ModelType::SwinUpernet,
            ModelType::BandIt,
            ModelType::ScNet,
            ModelType::BandItV2,
            ModelType::Apollo,
            ModelType::TsBsMamba2,
            ModelType::Conformer,
            ModelType::BsConformer,
            ModelType::ScNetTran,
            ModelType::ScNetMasked,
        ]
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TrainingConfig {
    pub model_type: ModelType,
    pub config_path: String,
    pub start_checkpoint: Option<String>,
    pub results_path: String,
    pub data_paths: Vec<String>,
    pub valid_path: Option<String>,
    pub num_workers: Option<usize>,
    pub device_ids: Option<Vec<usize>>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InferenceConfig {
    pub model_type: ModelType,
    pub config_path: String,
    pub start_checkpoint: String,
    pub input_folder: String,
    pub store_dir: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationConfig {
    pub model_type: ModelType,
    pub config_path: String,
    pub start_checkpoint: String,
    pub valid_path: String,
}

#[derive(Debug, Clone)]
pub struct TrainingProgress {
    pub epoch: usize,
    pub train_loss: f64,
    pub valid_loss: Option<f64>,
    pub sdr: Option<f64>,
    pub sir: Option<f64>,
    pub sar: Option<f64>,
    pub isr: Option<f64>,
    pub gpu_memory: Option<f64>,
    pub gpu_utilization: Option<f64>,
}

#[derive(Debug, Clone)]
pub struct InferenceResult {
    pub input_file: String,
    pub output_dir: String,
    pub duration: Option<f64>,
    pub success: bool,
    pub error_message: Option<String>,
}
