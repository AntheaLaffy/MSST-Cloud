use ratatui::{
    backend::CrosstermBackend,
    widgets::{Block, Borders, List, ListItem, Paragraph, Wrap},
    Frame, Terminal,
};
use crossterm::{
    event::{self, Event, KeyCode, KeyEventKind},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use std::io;
use std::time::Duration;

use crate::model::ModelType;

#[derive(Debug, Clone, PartialEq)]
pub enum Screen {
    Home,
    ModelSelection,
    Config,
    Training,
    Inference,
    Validation,
}

pub struct App {
    pub screen: Screen,
    pub selected_index: usize,
    pub previous_screen: Option<Screen>,
    pub help_visible: bool,
    pub selected_model: Option<ModelType>,
    pub should_quit: bool,
}

impl App {
    pub fn new() -> Self {
        App {
            screen: Screen::Home,
            selected_index: 0,
            previous_screen: None,
            help_visible: false,
            selected_model: None,
            should_quit: false,
        }
    }

    pub fn run(&mut self) -> io::Result<()> {
        let backend = CrosstermBackend::new(io::stdout());
        let mut terminal = Terminal::new(backend)?;
        
        if let Err(e) = enable_raw_mode() {
            eprintln!("Failed to enable raw mode: {}", e);
            return Err(e);
        }
        
        if let Err(e) = execute!(io::stdout(), EnterAlternateScreen) {
            eprintln!("Failed to enter alternate screen: {}", e);
            let _ = disable_raw_mode();
            return Err(e);
        }

        let result = loop {
            terminal.draw(|f| {
                self.draw(f);
            })?;

            if event::poll(Duration::from_millis(100))? {
                if let Event::Key(key) = event::read()? {
                    if key.kind == KeyEventKind::Press {
                        if self.help_visible {
                            self.help_visible = false;
                        } else {
                            match key.code {
                                KeyCode::Char('q') => {
                                    self.should_quit = true;
                                }
                                KeyCode::Char('h') => {
                                    self.help_visible = true;
                                }
                                KeyCode::Enter => {
                                    self.handle_enter();
                                }
                                KeyCode::Up => {
                                    self.handle_up();
                                }
                                KeyCode::Down => {
                                    self.handle_down();
                                }
                                KeyCode::Esc => {
                                    self.handle_esc();
                                }
                                _ => {}
                            }
                        }
                    }
                }
            }

            if self.should_quit {
                break Ok(());
            }
        };

        let _ = disable_raw_mode();
        let _ = execute!(io::stdout(), LeaveAlternateScreen);
        
        result
    }

    fn draw(&self, f: &mut Frame) {
        if self.help_visible {
            self.draw_help(f);
        } else {
            match self.screen {
                Screen::Home => self.draw_home(f),
                Screen::ModelSelection => self.draw_model_selection(f),
                Screen::Config => self.draw_config(f),
                Screen::Training => self.draw_training(f),
                Screen::Inference => self.draw_inference(f),
                Screen::Validation => self.draw_validation(f),
            }
        }
    }

    fn draw_help(&self, f: &mut Frame) {
        let title = Paragraph::new("Help")
            .block(Block::default().borders(Borders::ALL))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan));

        let help_text = Paragraph::new(
            "Keyboard Shortcuts:\n\
             \n\
             q - Quit\n\
             h - Show this help\n\
             Enter - Select\n\
             Arrow Up/Down - Navigate\n\
             Esc - Go back\n\
             \n\
             Press any key to dismiss..."
        )
        .wrap(Wrap { trim: false });

        let chunks = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .margin(1)
            .constraints([
                ratatui::layout::Constraint::Length(3),
                ratatui::layout::Constraint::Min(10),
            ])
            .split(f.size());

        f.render_widget(title, chunks[0]);
        f.render_widget(help_text, chunks[1]);
    }

    fn draw_home(&self, f: &mut Frame) {
        let title = Paragraph::new("Music Source Separation TUI")
            .block(Block::default().borders(Borders::ALL))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan));

        let menu_items = vec![
            "1. Model Selection",
            "2. Configuration",
            "3. Training",
            "4. Inference",
            "5. Validation",
            "q. Quit",
            "h. Help",
        ];

        let list_items: Vec<ListItem> = menu_items
            .iter()
            .enumerate()
            .map(|(i, item)| {
                if i == self.selected_index {
                    ListItem::new(*item)
                        .style(ratatui::style::Style::default()
                            .fg(ratatui::style::Color::Yellow)
                            .add_modifier(ratatui::style::Modifier::BOLD))
                } else {
                    ListItem::new(*item)
                        .style(ratatui::style::Style::default()
                            .fg(ratatui::style::Color::White))
                }
            })
            .collect();

        let menu = List::new(list_items)
            .block(Block::default().borders(Borders::ALL));

        let help_text = Paragraph::new("Use arrow keys to navigate, Enter to select")
            .wrap(Wrap { trim: false });

        let chunks = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .margin(1)
            .constraints([
                ratatui::layout::Constraint::Length(3),
                ratatui::layout::Constraint::Min(10),
                ratatui::layout::Constraint::Length(3),
            ])
            .split(f.size());

        f.render_widget(title, chunks[0]);
        f.render_widget(menu, chunks[1]);
        f.render_widget(help_text, chunks[2]);
    }

    fn draw_model_selection(&self, f: &mut Frame) {
        let title = Paragraph::new("Model Selection")
            .block(Block::default().borders(Borders::ALL))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan));

        let models = ModelType::all_models();
        let list_items: Vec<ListItem> = models
            .iter()
            .enumerate()
            .map(|(i, m)| {
                let text = format!("{} - {}", m.name(), m.description());
                if i == self.selected_index {
                    ListItem::new(text)
                        .style(ratatui::style::Style::default()
                            .fg(ratatui::style::Color::Yellow)
                            .add_modifier(ratatui::style::Modifier::BOLD))
                } else {
                    ListItem::new(text)
                        .style(ratatui::style::Style::default()
                            .fg(ratatui::style::Color::White))
                }
            })
            .collect();

        let list = List::new(list_items)
            .block(Block::default().borders(Borders::ALL));

        let chunks = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .margin(1)
            .constraints([
                ratatui::layout::Constraint::Length(3),
                ratatui::layout::Constraint::Min(10),
            ])
            .split(f.size());

        f.render_widget(title, chunks[0]);
        f.render_widget(list, chunks[1]);
    }

    fn draw_config(&self, f: &mut Frame) {
        let title = Paragraph::new("Configuration")
            .block(Block::default().borders(Borders::ALL))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan));

        let text = Paragraph::new("Configuration management - Coming soon!")
            .wrap(Wrap { trim: false });

        let chunks = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .margin(1)
            .constraints([
                ratatui::layout::Constraint::Length(3),
                ratatui::layout::Constraint::Min(10),
            ])
            .split(f.size());

        f.render_widget(title, chunks[0]);
        f.render_widget(text, chunks[1]);
    }

    fn draw_training(&self, f: &mut Frame) {
        let title = Paragraph::new("Training")
            .block(Block::default().borders(Borders::ALL))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan));

        let text = Paragraph::new("Training interface - Coming soon!")
            .wrap(Wrap { trim: false });

        let chunks = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .margin(1)
            .constraints([
                ratatui::layout::Constraint::Length(3),
                ratatui::layout::Constraint::Min(10),
            ])
            .split(f.size());

        f.render_widget(title, chunks[0]);
        f.render_widget(text, chunks[1]);
    }

    fn draw_inference(&self, f: &mut Frame) {
        let title = Paragraph::new("Inference")
            .block(Block::default().borders(Borders::ALL))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan));

        let text = Paragraph::new("Inference interface - Coming soon!")
            .wrap(Wrap { trim: false });

        let chunks = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .margin(1)
            .constraints([
                ratatui::layout::Constraint::Length(3),
                ratatui::layout::Constraint::Min(10),
            ])
            .split(f.size());

        f.render_widget(title, chunks[0]);
        f.render_widget(text, chunks[1]);
    }

    fn draw_validation(&self, f: &mut Frame) {
        let title = Paragraph::new("Validation")
            .block(Block::default().borders(Borders::ALL))
            .style(ratatui::style::Style::default().fg(ratatui::style::Color::Cyan));

        let text = Paragraph::new("Validation interface - Coming soon!")
            .wrap(Wrap { trim: false });

        let chunks = ratatui::layout::Layout::default()
            .direction(ratatui::layout::Direction::Vertical)
            .margin(1)
            .constraints([
                ratatui::layout::Constraint::Length(3),
                ratatui::layout::Constraint::Min(10),
            ])
            .split(f.size());

        f.render_widget(title, chunks[0]);
        f.render_widget(text, chunks[1]);
    }

    fn show_help(&self) {
    }

    fn handle_enter(&mut self) {
        match self.screen {
            Screen::Home => {
                self.previous_screen = Some(Screen::Home);
                self.screen = Screen::ModelSelection;
                self.selected_index = 0;
            }
            Screen::ModelSelection => {
                let models = ModelType::all_models();
                if self.selected_index < models.len() {
                    self.selected_model = Some(models[self.selected_index].clone());
                }
            }
            _ => {}
        }
    }

    fn handle_up(&mut self) {
        if self.selected_index > 0 {
            self.selected_index -= 1;
        }
    }

    fn handle_down(&mut self) {
        let max_index = match self.screen {
            Screen::Home => 6,
            Screen::ModelSelection => ModelType::all_models().len() - 1,
            _ => 0,
        };
        if self.selected_index < max_index {
            self.selected_index += 1;
        }
    }

    fn handle_esc(&mut self) {
        match self.screen {
            Screen::ModelSelection | Screen::Config | Screen::Training | Screen::Inference | Screen::Validation => {
                self.previous_screen = Some(self.screen.clone());
                self.screen = Screen::Home;
                self.selected_index = 0;
            }
            Screen::Home => {
                self.should_quit = true;
            }
        }
    }
}
