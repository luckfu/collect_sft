#!/usr/bin/env python3
"""
Simple Endpoint Configuration Editor
A beautiful and simple CUI for editing endpoint_config.json
"""

import json
import os
import sys
from typing import Dict, List, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.columns import Columns
from rich import print as rprint

console = Console()

class SimpleEndpointEditor:
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
    
    def display_banner(self):
        """Display beautiful banner"""
        banner = """
[bold cyan]╔══════════════════════════════════════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]                     [bold white]🚀 Endpoint Configuration Editor[/bold white]                    [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]              [dim]Beautiful CUI for managing endpoint configs[/dim]               [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════════════════════════════════════╝[/bold cyan]
        """
        console.print(banner)
    
    def display_endpoints(self):
        """Display all endpoints in a beautiful table"""
        endpoints = self.config.get("endpoints", {})
        
        if not endpoints:
            console.print("\n[yellow]📭 No endpoints configured[/yellow]")
            return
        
        table = Table(title="[bold cyan]🌐 Configured Endpoints[/bold cyan]", show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan", no_wrap=True, width=15)
        table.add_column("Base URL", style="green", width=35)
        table.add_column("Models", style="yellow", width=25)
        table.add_column("Features", style="blue", width=15)
        table.add_column("Auth Type", style="magenta", width=10)
        
        for name, config in endpoints.items():
            base_url = config.get("base_url", "N/A")
            models = config.get("models", [])
            models_display = f"{len(models)} models" if models else "No models"
            
            features = []
            if config.get("chat_completion_path"):
                features.append("💬")
            if config.get("embeddings_path"):
                features.append("📊")
            if config.get("rerank_path"):
                features.append("🔄")
            if config.get("anthropic_path"):
                features.append("🤖")
            
            features_display = " ".join(features) if features else "Basic"
            auth_type = config.get("auth_type", "unknown")
            
            table.add_row(name, base_url, models_display, features_display, auth_type)
        
        console.print(table)
    
    def add_endpoint(self):
        """Add a new endpoint with interactive prompts"""
        console.print("\n[bold green]➕ Adding New Endpoint[/bold green]")
        console.print("[dim]Press Enter to use defaults, Ctrl+C to cancel[/dim]")
        
        try:
            name = Prompt.ask("[cyan]Endpoint name[/cyan]").strip()
            if not name:
                console.print("[red]❌ Name is required[/red]")
                return
            
            if name in self.config.get("endpoints", {}):
                console.print(f"[red]❌ Endpoint '{name}' already exists[/red]")
                return
            
            base_url = Prompt.ask("[cyan]Base URL[/cyan]", default="https://api.example.com")
            auth_type = Prompt.ask(
                "[cyan]Auth type[/cyan]", 
                choices=["bearer", "api_key", "none"], 
                default="bearer"
            )
            
            models_str = Prompt.ask("[cyan]Models (comma-separated)[/cyan]", default="model1,model2")
            models = [m.strip() for m in models_str.split(",") if m.strip()]
            
            config = {
                "base_url": base_url,
                "auth_type": auth_type,
                "models": models
            }
            
            if Confirm.ask("[dim]Add chat completion path?[/dim]", default=True):
                config["chat_completion_path"] = Prompt.ask(
                    "[cyan]Chat completion path[/cyan]", 
                    default="/v1/chat/completions"
                )
            
            if Confirm.ask("[dim]Add embeddings support?[/dim]", default=False):
                config["embeddings_path"] = Prompt.ask(
                    "[cyan]Embeddings path[/cyan]", 
                    default="/v1/embeddings"
                )
                embeddings_models_str = Prompt.ask(
                    "[cyan]Embeddings models[/cyan]", 
                    default="embedding-model"
                )
                config["embeddings_models"] = [m.strip() for m in embeddings_models_str.split(",") if m.strip()]
            
            if Confirm.ask("[dim]Add rerank support?[/dim]", default=False):
                config["rerank_path"] = Prompt.ask(
                    "[cyan]Rerank path[/cyan]", 
                    default="/v1/rerank"
                )
                rerank_models_str = Prompt.ask(
                    "[cyan]Rerank models[/cyan]", 
                    default="rerank-model"
                )
                config["rerank_models"] = [m.strip() for m in rerank_models_str.split(",") if m.strip()]
            
            if "endpoints" not in self.config:
                self.config["endpoints"] = {}
            
            self.config["endpoints"][name] = config
            
            if self.save_config():
                console.print(f"[green]✅ Endpoint '{name}' added successfully![/green]")
            else:
                console.print("[red]❌ Failed to save endpoint[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]⚡ Cancelled[/yellow]")
    
    def edit_endpoint(self):
        """Edit an existing endpoint"""
        endpoints = self.config.get("endpoints", {})
        if not endpoints:
            console.print("[yellow]📭 No endpoints to edit[/yellow]")
            return
        
        endpoint_names = list(endpoints.keys())
        name = Prompt.ask(
            "[cyan]Choose endpoint to edit[/cyan]",
            choices=endpoint_names
        )
        
        if not name:
            return
        
        config = endpoints[name]
        console.print(f"\n[bold yellow]✏️  Editing: {name}[/bold yellow]")
        
        try:
            base_url = Prompt.ask("[cyan]Base URL[/cyan]", default=config.get("base_url", ""))
            auth_type = Prompt.ask(
                "[cyan]Auth type[/cyan]",
                choices=["bearer", "api_key", "none"],
                default=config.get("auth_type", "bearer")
            )
            
            models_str = ",".join(config.get("models", []))
            models_input = Prompt.ask("[cyan]Models (comma-separated)[/cyan]", default=models_str)
            models = [m.strip() for m in models_input.split(",") if m.strip()]
            
            config.update({
                "base_url": base_url,
                "auth_type": auth_type,
                "models": models
            })
            
            # Handle optional paths
            optional_paths = [
                ("chat_completion_path", "/v1/chat/completions"),
                ("embeddings_path", "/v1/embeddings"),
                ("rerank_path", "/v1/rerank"),
                ("anthropic_path", "/v1/messages")
            ]
            
            for path_key, default_path in optional_paths:
                current_value = config.get(path_key, "")
                if current_value or Confirm.ask(f"[dim]Add {path_key}?[/dim]", default=False):
                    new_value = Prompt.ask(
                        f"[cyan]{path_key}[/cyan]",
                        default=current_value or default_path
                    )
                    if new_value.strip():
                        config[path_key] = new_value.strip()
                    elif path_key in config:
                        del config[path_key]
            
            # Handle optional model lists
            optional_models = [
                ("embeddings_models", "embedding-models"),
                ("rerank_models", "rerank-models")
            ]
            
            for model_key, default_models in optional_models:
                current_models = ",".join(config.get(model_key, []))
                if current_models or config.get(model_key.replace("_models", "_path")):
                    models_input = Prompt.ask(
                        f"[cyan]{model_key}[/cyan]",
                        default=current_models or default_models
                    )
                    model_list = [m.strip() for m in models_input.split(",") if m.strip()]
                    if model_list:
                        config[model_key] = model_list
                    elif model_key in config:
                        del config[model_key]
            
            if self.save_config():
                console.print(f"[green]✅ Endpoint '{name}' updated successfully![/green]")
            else:
                console.print("[red]❌ Failed to update endpoint[/red]")
                
        except KeyboardInterrupt:
            console.print("\n[yellow]⚡ Cancelled[/yellow]")
    
    def delete_endpoint(self):
        """Delete an endpoint"""
        endpoints = self.config.get("endpoints", {})
        if not endpoints:
            console.print("[yellow]📭 No endpoints to delete[/yellow]")
            return
        
        endpoint_names = list(endpoints.keys())
        name = Prompt.ask(
            "[cyan]Choose endpoint to delete[/cyan]",
            choices=endpoint_names
        )
        
        if name and Confirm.ask(f"[red]⚠️  Are you sure you want to delete '{name}'?[/red]"):
            del self.config["endpoints"][name]
            if self.save_config():
                console.print(f"[green]✅ Endpoint '{name}' deleted successfully![/green]")
            else:
                console.print("[red]❌ Failed to delete endpoint[/red]")
    
    def run(self):
        """Main application loop"""
        try:
            while True:
                os.system('clear' if os.name == 'posix' else 'cls')
                self.display_banner()
                self.display_endpoints()
                
                console.print("\n" + "─" * 80)
                choices = [
                    "[green]📥 Add endpoint[/green]",
                    "[yellow]✏️  Edit endpoint[/yellow]",
                    "[red]🗑️  Delete endpoint[/red]",
                    "[blue]💾 Save config[/blue]",
                    "[magenta]❌ Exit[/magenta]"
                ]
                
                action = Prompt.ask(
                    "\n[bold cyan]Choose action[/bold cyan]",
                    choices=["add", "edit", "delete", "save", "exit"],
                    default="exit"
                )
                
                if action == "add":
                    self.add_endpoint()
                    input("\n[dim]Press Enter to continue...[/dim]")
                elif action == "edit":
                    self.edit_endpoint()
                    input("\n[dim]Press Enter to continue...[/dim]")
                elif action == "delete":
                    self.delete_endpoint()
                    input("\n[dim]Press Enter to continue...[/dim]")
                elif action == "save":
                    if self.save_config():
                        console.print("[green]💾 Configuration saved successfully![/green]")
                    else:
                        console.print("[red]❌ Failed to save configuration[/red]")
                    input("\n[dim]Press Enter to continue...[/dim]")
                elif action == "exit":
                    console.print("\n[bold green]👋 Thank you for using Endpoint Configuration Editor![/bold green]")
                    break
                    
        except KeyboardInterrupt:
            console.print("\n\n[bold green]👋 Thank you for using Endpoint Configuration Editor![/bold green]")

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        console.print("[bold cyan]Endpoint Configuration Editor[/bold cyan]")
        console.print("Usage: python simple_editor.py")
        console.print("A beautiful CUI for editing endpoint_config.json")
        return
    
    editor = SimpleEndpointEditor()
    editor.run()

if __name__ == "__main__":
    main()