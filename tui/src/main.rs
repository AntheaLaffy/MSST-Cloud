mod config;
mod model;
mod training;
mod inference;
mod ui;

use ui::App;
use std::env;
use std::path::Path;

fn main() -> anyhow::Result<()> {
    let current_exe = env::current_exe()?;
    let exe_dir = current_exe.parent()
        .ok_or_else(|| anyhow::anyhow!("Cannot get executable directory"))?;
    
    let project_root = find_project_root(exe_dir)?;
    env::set_current_dir(&project_root)?;
    
    println!("TUI running from: {}", project_root.display());
    
    let mut app = App::new();
    app.run()?;
    Ok(())
}

fn find_project_root(start_dir: &Path) -> anyhow::Result<&Path> {
    let mut current = start_dir;
    
    loop {
        if is_project_root(current) {
            return Ok(current);
        }
        
        match current.parent() {
            Some(parent) => current = parent,
            None => return Err(anyhow::anyhow!("Cannot find project root")),
        }
    }
}

fn is_project_root(dir: &Path) -> bool {
    dir.join("train.py").exists() 
        && dir.join("inference.py").exists()
        && dir.join("README.md").exists()
}
