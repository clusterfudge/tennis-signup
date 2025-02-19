#!/usr/bin/env python3

from datetime import datetime
import pytz
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from storage import Storage

def format_time(timestamp, from_tz='UTC', to_tz='US/Pacific'):
    """Convert and format time between timezones."""
    utc_time = datetime.fromtimestamp(timestamp, pytz.UTC)
    pacific_time = utc_time.astimezone(pytz.timezone(to_tz))
    return f"{utc_time.strftime('%Y-%m-%d %H:%M')} UTC / {pacific_time.strftime('%Y-%m-%d %H:%M')} PT"

def main():
    console = Console()
    storage = Storage('storage')

    # Get latest schedule and plan
    schedule_id, schedule = storage.latest("sched")
    plan_id, plan = storage.latest("plan")

    if not schedule:
        console.print("[red]No schedule found![/red]")
        return

    # Create schedule table
    table = Table(title="Latest Schedule & Plan", show_header=True, header_style="bold magenta")
    table.add_column("Slug", width=8)
    table.add_column("Title", width=50)
    table.add_column("Time")
    table.add_column("Status", justify="center")

    # Create a set of planned slugs for easy lookup
    planned_slugs = set(plan.keys()) if plan else set()

    for entry in sorted(schedule, key=lambda x: x['timestamp']):
        slug = entry['slug']
        time_str = format_time(entry['timestamp'])
        
        # Determine status
        planned = slug in planned_slugs
        planned_entry = plan.get(slug, {}) if plan else {}
        booked = planned_entry.get('booked', False) if planned else False
        synced = planned_entry.get('synced', False) if planned else False
        
        status = []
        if planned:
            status.append("[green]PLANNED[/green]")
        if booked:
            status.append("[blue]BOOKED[/blue]")
        if synced:
            status.append("[yellow]SYNCED[/yellow]")
        
        status_str = " ".join(status) if status else "[grey]--[/grey]"
        
        table.add_row(
            slug,
            entry.get('description', ''),
            time_str,
            status_str
        )

    # Display the information
    console.print(Panel(f"Schedule ID: {schedule_id}\nPlan ID: {plan_id}", title="IDs"))
    console.print(table)

if __name__ == "__main__":
    main()