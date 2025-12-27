# Music Source Separation TUI

A terminal-based user interface (TUI) for music source separation training and inference, built with Rust and ratatui.

## Features

- **Model Selection**: Choose from 16 supported music separation models
- **Configuration Management**: Edit and manage YAML configuration files
- **Training Interface**: Monitor training progress with real-time updates
- **Inference Interface**: Run batch inference on audio files
- **Validation Interface**: Track model performance metrics (SDR, SIR, SAR, ISR)

## Supported Models

1. MDX23C - KUIELab TFC TDF v3 architecture
2. Demucs4HT - Hybrid transformer architecture
3. VitLarge23 - Vision transformer based
4. TorchSeg - Segmentation models with 800+ encoders
5. Band Split RoFormer - Rotary attention with band splitting
6. Mel-Band RoFormer - Mel-spectrogram band splitting
7. Swin Upernet - Swin transformer with UperNet
8. BandIt Plus - Band-limited attention
9. SCNet - Spectral convolution network
10. BandIt v2 - Improved band-limited attention
11. Apollo - Advanced separation architecture
12. TS BSMamba2 - State space model
13. Conformer - Convolution-augmented transformer
14. BS Conformer - Band split conformer
15. SCNet Tran - Transformer variant
16. SCNet Masked - Masked variant

## Installation

### Prerequisites

- Rust toolchain (1.70 or later)
- Python 3.8 or later
- Python dependencies from the main project

### Build from Source

```bash
cd tui
cargo build --release
```

The compiled binary will be available at `target/release/mss_tui.exe` (Windows) or `target/release/mss_tui` (Linux/macOS).

## Usage

### Running the TUI

```bash
cd tui
cargo run
```

Or use the compiled binary:

```bash
./target/release/mss_tui
```

### Keyboard Shortcuts

- `q` - Quit the application
- `h` - Show help
- `Enter` - Select menu item
- `Arrow Up/Down` - Navigate through lists
- `Esc` - Go back to previous screen

## Project Structure

```
tui/
├── src/
│   ├── main.rs          # Application entry point
│   ├── ui.rs            # TUI framework and screens
│   ├── model.rs         # Model types and data structures
│   ├── config.rs        # Configuration management
│   ├── training.rs      # Training process management
│   └── inference.rs     # Inference process management
├── Cargo.toml          # Rust dependencies
└── README.md           # This file
```

## Development

### Adding New Features

The TUI is built with a modular architecture:

1. **Model Types** (`src/model.rs`): Define new model types and configurations
2. **Configuration** (`src/config.rs`): Manage YAML configuration files
3. **Training** (`src/training.rs`): Integrate with Python training scripts
4. **Inference** (`src/inference.rs`): Integrate with Python inference scripts
5. **UI** (`src/ui.rs`): Add new screens and widgets

### Running Tests

```bash
cargo test
```

### Checking Code

```bash
cargo check
```

## Integration with Python Backend

The TUI integrates with the existing Python scripts through subprocess calls:

- `train.py` - Training process
- `inference.py` - Inference process
- `valid.py` - Validation process

All Python scripts should be in the parent directory of the TUI project.

## License

This project is part of the Music Source Separation Training project. Refer to the main project license for details.

## Contributing

Contributions are welcome! Please ensure:

1. Code follows Rust best practices
2. All tests pass (`cargo test`)
3. Code is properly documented
4. Changes are compatible with the Python backend

## Roadmap

- [ ] Complete configuration UI with file browser
- [ ] Implement training progress monitoring
- [ ] Add inference batch processing
- [ ] Implement validation metrics visualization
- [ ] Add color themes (dark, light, high contrast)
- [ ] Create startup wizard for first-time users
- [ ] Add configuration persistence
