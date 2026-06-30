#!/usr/bin/env python3
"""
Endpoint Configuration Editor
A beautiful CUI terminal interface for editing endpoint_config.json
"""

import json
import os
import sys
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.prompt import Prompt, Confirm
from rich.columns import Columns
from rich.console import Group
from textual.app import App, ComposeResult
from textual.widgets import (
    Header, Footer, DataTable, Button, Input, Static, Select, 
    TabbedContent, TabPane, Checkbox, Label
)
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.binding import Binding
import click

console = Console()

class EndpointConfig:
    def __init__(self, config_path: str = "endpoint_config.json"):
        self.config_path = config_path
        self.config = self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return {"endpoints": {}}
        except Exception as e:
            console.print(f"[red]Error loading config: {e}[/red]")
            return {"endpoints": {}}
    
    def save_config(self) -> bool:
        """Save configuration to JSON file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            console.print(f"[red]Error saving config: {e}[/red]")
            return False
    
    def get_endpoints(self) -> Dict[str, Dict[str, Any]]:
        """Get all endpoints"""
        return self.config.get("endpoints", {})
    
    def add_endpoint(self, name: str, config: Dict[str, Any]) -> bool:
        """Add a new endpoint"""
        if "endpoints" not in self.config:
            self.config["endpoints"] = {}
        self.config["endpoints"][name] = config
        return self.save_config()
    
    def update_endpoint(self, name: str, config: Dict[str, Any]) -> bool:
        """Update an existing endpoint"""
        if name in self.config.get("endpoints", {}):
            self.config["endpoints"][name] = config
            return self.save_config()
        return False
    
    def delete_endpoint(self, name: str) -> bool:
        """Delete an endpoint"""
        if name in self.config.get("endpoints", {}):
            del self.config["endpoints"][name]
            return self.save_config()
        return False

class EndpointListScreen(Screen):
    """Main screen showing list of endpoints"""
    
    BINDINGS = [
        Binding("a", "add_endpoint", "Add Endpoint"),
        Binding("d", "delete_endpoint", "Delete Endpoint"),
        Binding("e", "edit_endpoint", "Edit Endpoint"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+s", "save", "Save"),
    ]
    
    def __init__(self, config_manager: EndpointConfig):
        super().__init__()
        self.config_manager = config_manager
        self.data_table = None
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static("[bold cyan]Endpoint Configuration Editor[/bold cyan]", classes="title"),
            DataTable(id="endpoints_table"),
            Static("[dim]Press 'a' to add, 'e' to edit, 'd' to delete, 'q' to quit[/dim]", classes="help"),
            id="main_container"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the screen"""
        table = self.query_one("#endpoints_table", DataTable)
        table.add_columns("Name", "Base URL", "Models Count", "Auth Type")
        self.refresh_table()
    
    def refresh_table(self) -> None:
        """Refresh the endpoints table"""
        table = self.query_one("#endpoints_table", DataTable)
        table.clear()
        
        endpoints = self.config_manager.get_endpoints()
        for name, config in endpoints.items():
            models = config.get("models", [])
            models_count = len(models) if isinstance(models, list) else 0
            auth_type = config.get("auth_type", "unknown")
            base_url = config.get("base_url", "N/A")
            
            table.add_row(
                name,
                base_url,
                str(models_count),
                auth_type
            )
    
    def action_add_endpoint(self) -> None:
        """Add a new endpoint"""
        self.app.push_screen(EndpointEditScreen(self.config_manager))
    
    def action_edit_endpoint(self) -> None:
        """Edit selected endpoint"""
        table = self.query_one("#endpoints_table", DataTable)
        if table.cursor_row is not None:
            endpoint_name = table.get_cell_at(table.cursor_row, 0)
            self.app.push_screen(EndpointEditScreen(self.config_manager, endpoint_name))
    
    def action_delete_endpoint(self) -> None:
        """Delete selected endpoint"""
        table = self.query_one("#endpoints_table", DataTable)
        if table.cursor_row is not None:
            endpoint_name = table.get_cell_at(table.cursor_row, 0)
            if Confirm.ask(f"Delete endpoint '{endpoint_name}'?"):
                self.config_manager.delete_endpoint(endpoint_name)
                self.refresh_table()
    
    def action_save(self) -> None:
        """Save configuration"""
        if self.config_manager.save_config():
            self.notify("Configuration saved successfully!")
        else:
            self.notify("Failed to save configuration", severity="error")

class EndpointEditScreen(Screen):
    """Screen for editing an endpoint"""
    
    BINDINGS = [
        Binding("ctrl+s", "save", "Save"),
        Binding("escape", "cancel", "Cancel"),
    ]
    
    def __init__(self, config_manager: EndpointConfig, endpoint_name: str = None):
        super().__init__()
        self.config_manager = config_manager
        self.endpoint_name = endpoint_name
        self.is_new = endpoint_name is None
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Static(
                f"[bold cyan]{'Add New' if self.is_new else 'Edit'} Endpoint[/bold cyan]",
                classes="title"
            ),
            Vertical(
                Label("Endpoint Name:"),
                Input(
                    placeholder="Enter endpoint name...",
                    id="name_input",
                    value="" if self.is_new else self.endpoint_name
                ),
                Label("Base URL:"),
                Input(
                    placeholder="https://api.example.com",
                    id="base_url_input"
                ),
                Label("Chat Completion Path:"),
                Input(
                    placeholder="/v1/chat/completions",
                    id="chat_path_input"
                ),
                Label("Embeddings Path:"),
                Input(
                    placeholder="/v1/embeddings (optional)",
                    id="embeddings_path_input"
                ),
                Label("Rerank Path:"),
                Input(
                    placeholder="/v1/rerank (optional)",
                    id="rerank_path_input"
                ),
                Label("Anthropic Path:"),
                Input(
                    placeholder="/v1/messages (optional)",
                    id="anthropic_path_input"
                ),
                Label("Models (comma-separated):"),
                Input(
                    placeholder="model1,model2,model3",
                    id="models_input"
                ),
                Label("Embeddings Models (comma-separated):"),
                Input(
                    placeholder="embedding-model1,embedding-model2 (optional)",
                    id="embeddings_models_input"
                ),
                Label("Rerank Models (comma-separated):"),
                Input(
                    placeholder="rerank-model1,rerank-model2 (optional)",
                    id="rerank_models_input"
                ),
                Label("Auth Type:"),
                Select(
                    [("Bearer", "bearer"), ("API Key", "api_key"), ("None", "none")],
                    id="auth_type_select",
                    value="bearer"
                ),
                Button("Save", id="save_button", variant="primary"),
                Button("Cancel", id="cancel_button", variant="error"),
                classes="form_container"
            ),
            id="edit_container"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Initialize the form with existing data"""
        if not self.is_new:
            endpoints = self.config_manager.get_endpoints()
            if self.endpoint_name in endpoints:
                config = endpoints[self.endpoint_name]
                
                # Fill form with existing data
                self.query_one("#base_url_input", Input).value = config.get("base_url", "")
                self.query_one("#chat_path_input", Input).value = config.get("chat_completion_path", "")
                self.query_one("#embeddings_path_input", Input).value = config.get("embeddings_path", "")
                self.query_one("#rerank_path_input", Input).value = config.get("rerank_path", "")
                self.query_one("#anthropic_path_input", Input).value = config.get("anthropic_path", "")
                
                models = config.get("models", [])
                self.query_one("#models_input", Input).value = ",".join(models) if models else ""
                
                embeddings_models = config.get("embeddings_models", [])
                self.query_one("#embeddings_models_input", Input).value = ",".join(embeddings_models) if embeddings_models else ""
                
                rerank_models = config.get("rerank_models", [])
                self.query_one("#rerank_models_input", Input).value = ",".join(rerank_models) if rerank_models else ""
                
                auth_type = config.get("auth_type", "bearer")
                self.query_one("#auth_type_select", Select).value = auth_type
                
                if self.is_new:
                    self.query_one("#name_input", Input).focus()
                else:
                    self.query_one("#base_url_input", Input).focus()
    
    def action_save(self) -> None:
        """Save the endpoint configuration"""
        self.save_endpoint()
    
    def save_endpoint(self) -> None:
        """Save the endpoint"""
        name = self.query_one("#name_input", Input).value.strip()
        if not name:
            self.notify("Endpoint name is required", severity="error")
            return
        
        if self.is_new and name in self.config_manager.get_endpoints():
            self.notify("Endpoint name already exists", severity="error")
            return
        
        if not self.is_new and name != self.endpoint_name and name in self.config_manager.get_endpoints():
            self.notify("Endpoint name already exists", severity="error")
            return
        
        config = {
            "base_url": self.query_one("#base_url_input", Input).value.strip(),
            "auth_type": self.query_one("#auth_type_select", Select).value
        }
        
        # Add optional fields only if they have values
        chat_path = self.query_one("#chat_path_input", Input).value.strip()
        if chat_path:
            config["chat_completion_path"] = chat_path
        
        embeddings_path = self.query_one("#embeddings_path_input", Input).value.strip()
        if embeddings_path:
            config["embeddings_path"] = embeddings_path
        
        rerank_path = self.query_one("#rerank_path_input", Input).value.strip()
        if rerank_path:
            config["rerank_path"] = rerank_path
        
        anthropic_path = self.query_one("#anthropic_path_input", Input).value.strip()
        if anthropic_path:
            config["anthropic_path"] = anthropic_path
        
        models = [m.strip() for m in self.query_one("#models_input", Input).value.split(",") if m.strip()]
        if models:
            config["models"] = models
        
        embeddings_models = [m.strip() for m in self.query_one("#embeddings_models_input", Input).value.split(",") if m.strip()]
        if embeddings_models:
            config["embeddings_models"] = embeddings_models
        
        rerank_models = [m.strip() for m in self.query_one("#rerank_models_input", Input).value.split(",") if m.strip()]
        if rerank_models:
            config["rerank_models"] = rerank_models
        
        # If editing existing endpoint with different name, delete old one
        if not self.is_new and name != self.endpoint_name:
            self.config_manager.delete_endpoint(self.endpoint_name)
        
        if self.config_manager.add_endpoint(name, config):
            self.notify("Endpoint saved successfully!")
            self.app.pop_screen()
        else:
            self.notify("Failed to save endpoint", severity="error")
    
    def action_cancel(self) -> None:
        """Cancel editing"""
        self.app.pop_screen()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "save_button":
            self.save_endpoint()
        elif event.button.id == "cancel_button":
            self.app.pop_screen()

class EndpointEditorApp(App):
    """Main application class"""
    
    CSS = """
    .title {
        text-align: center;
        color: $accent;
        text-style: bold;
        margin: 1;
    }
    
    .help {
        text-align: center;
        color: $text-muted;
        margin: 1;
    }
    
    #main_container {
        margin: 1;
    }
    
    #endpoints_table {
        height: 80%;
        margin: 1;
    }
    
    #edit_container {
        margin: 1;
        height: 100%;
    }
    
    .form_container {
        margin: 1;
        height: 90%;
    }
    
    Label {
        margin-top: 1;
    }
    
    Input {
        width: 100%;
    }
    
    Button {
        margin: 1;
    }
    """
    
    def __init__(self, config_path: str = "endpoint_config.json"):
        super().__init__()
        self.config_manager = EndpointConfig(config_path)
    
    def on_mount(self) -> None:
        """Called when app is mounted"""
        self.push_screen(EndpointListScreen(self.config_manager))

def main():
    """Main function for CLI usage"""
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        # CLI mode using rich console
        config = EndpointConfig()
        
        console.print(Panel.fit(
            "[bold cyan]Endpoint Configuration Editor[/bold cyan]\n"
            "A simple CLI tool for managing endpoint configurations",
            border_style="cyan"
        ))
        
        while True:
            endpoints = config.get_endpoints()
            
            if not endpoints:
                console.print("[yellow]No endpoints configured[/yellow]")
            else:
                table = Table(title="Configured Endpoints")
                table.add_column("Name", style="cyan", no_wrap=True)
                table.add_column("Base URL", style="green")
                table.add_column("Models Count", style="yellow")
                table.add_column("Auth Type", style="magenta")
                
                for name, endpoint_config in endpoints.items():
                    models = endpoint_config.get("models", [])
                    models_count = len(models) if isinstance(models, list) else 0
                    table.add_row(
                        name,
                        endpoint_config.get("base_url", "N/A"),
                        str(models_count),
                        endpoint_config.get("auth_type", "unknown")
                    )
                
                console.print(table)
            
            action = Prompt.ask(
                "\nChoose action",
                choices=["add", "edit", "delete", "save", "quit"],
                default="quit"
            )
            
            if action == "add":
                name = Prompt.ask("Endpoint name")
                if name in endpoints:
                    console.print("[red]Endpoint already exists[/red]")
                    continue
                
                base_url = Prompt.ask("Base URL")
                auth_type = Prompt.ask("Auth type", choices=["bearer", "api_key", "none"], default="bearer")
                models_str = Prompt.ask("Models (comma-separated)")
                models = [m.strip() for m in models_str.split(",") if m.strip()]
                
                endpoint_config = {
                    "base_url": base_url,
                    "auth_type": auth_type,
                    "models": models
                }
                
                if Confirm.ask("Add chat completion path?"):
                    endpoint_config["chat_completion_path"] = Prompt.ask("Chat completion path", default="/v1/chat/completions")
                
                if Confirm.ask("Add embeddings support?"):
                    endpoint_config["embeddings_path"] = Prompt.ask("Embeddings path", default="/v1/embeddings")
                    embeddings_models_str = Prompt.ask("Embeddings models (comma-separated)")
                    endpoint_config["embeddings_models"] = [m.strip() for m in embeddings_models_str.split(",") if m.strip()]
                
                if Confirm.ask("Add rerank support?"):
                    endpoint_config["rerank_path"] = Prompt.ask("Rerank path", default="/v1/rerank")
                    rerank_models_str = Prompt.ask("Rerank models (comma-separated)")
                    endpoint_config["rerank_models"] = [m.strip() for m in rerank_models_str.split(",") if m.strip()]
                
                config.add_endpoint(name, endpoint_config)
                console.print("[green]Endpoint added successfully![/green]")
            
            elif action == "edit":
                if not endpoints:
                    console.print("[yellow]No endpoints to edit[/yellow]")
                    continue
                
                name = Prompt.ask("Endpoint name to edit", choices=list(endpoints.keys()))
                endpoint_config = endpoints[name]
                
                console.print(f"\n[bold]Editing: {name}[/bold]")
                
                base_url = Prompt.ask("Base URL", default=endpoint_config.get("base_url", ""))
                auth_type = Prompt.ask("Auth type", choices=["bearer", "api_key", "none"], default=endpoint_config.get("auth_type", "bearer"))
                models_str = ",".join(endpoint_config.get("models", []))
                models = [m.strip() for m in Prompt.ask("Models (comma-separated)", default=models_str).split(",") if m.strip()]
                
                endpoint_config.update({
                    "base_url": base_url,
                    "auth_type": auth_type,
                    "models": models
                })
                
                if Confirm.ask("Update chat completion path?"):
                    current = endpoint_config.get("chat_completion_path", "/v1/chat/completions")
                    endpoint_config["chat_completion_path"] = Prompt.ask("Chat completion path", default=current)
                
                if Confirm.ask("Update embeddings?"):
                    if "embeddings_path" not in endpoint_config:
                        endpoint_config["embeddings_path"] = "/v1/embeddings"
                    current = endpoint_config.get("embeddings_path", "/v1/embeddings")
                    endpoint_config["embeddings_path"] = Prompt.ask("Embeddings path", default=current)
                    
                    current_models = ",".join(endpoint_config.get("embeddings_models", []))
                    embeddings_models = [m.strip() for m in Prompt.ask("Embeddings models", default=current_models).split(",") if m.strip()]
                    endpoint_config["embeddings_models"] = embeddings_models
                
                if Confirm.ask("Update rerank?"):
                    if "rerank_path" not in endpoint_config:
                        endpoint_config["rerank_path"] = "/v1/rerank"
                    current = endpoint_config.get("rerank_path", "/v1/rerank")
                    endpoint_config["rerank_path"] = Prompt.ask("Rerank path", default=current)
                    
                    current_models = ",".join(endpoint_config.get("rerank_models", []))
                    rerank_models = [m.strip() for m in Prompt.ask("Rerank models", default=current_models).split(",") if m.strip()]
                    endpoint_config["rerank_models"] = rerank_models
                
                config.update_endpoint(name, endpoint_config)
                console.print("[green]Endpoint updated successfully![/green]")
            
            elif action == "delete":
                if not endpoints:
                    console.print("[yellow]No endpoints to delete[/yellow]")
                    continue
                
                name = Prompt.ask("Endpoint name to delete", choices=list(endpoints.keys()))
                if Confirm.ask(f"Delete endpoint '{name}'?"):
                    config.delete_endpoint(name)
                    console.print("[green]Endpoint deleted successfully![/green]")
            
            elif action == "save":
                if config.save_config():
                    console.print("[green]Configuration saved successfully![/green]")
                else:
                    console.print("[red]Failed to save configuration[/red]")
            
            elif action == "quit":
                break
    else:
        # TUI mode using textual
        app = EndpointEditorApp()
        app.run()

if __name__ == "__main__":
    main()