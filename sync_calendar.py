#!/usr/bin/env python3
import cal
import storage
import os
from rich.console import Console
from rich.table import Table
from datetime import datetime
import pytz

def format_timestamp(ts: float, tz_name: str) -> str:
    """Format timestamp for a specific timezone"""
    tz = pytz.timezone(tz_name)
    dt = datetime.fromtimestamp(ts, pytz.UTC)
    if tz_name != 'UTC':
        dt = dt.astimezone(tz)
    return dt.strftime('%Y-%m-%d %H:%M %Z')

def main():
    console = Console()
    
    # Initialize the storage
    db = storage.Storage('./storage')
    
    # Get the latest plan
    _, plan = db.latest('plan')
    
    if not plan:
        console.print("[red]No plan found to sync[/red]")
        return

    # Create table for output
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Event Title")
    table.add_column("Pacific Time")
    table.add_column("UTC")
    table.add_column("Status")

    # Sync the plan to calendar
    synced_events = cal.sync_plan_to_calendar(db, plan, os.environ.get('SHARED_CALENDAR_ID'))
    
    if not synced_events:
        console.print("[yellow]No new events to sync[/yellow]")
        return

    for event in synced_events:
        if event:  # Some events might be None if sync failed
            # Extract start time from the event
            event_time = event['start'].get('dateTime')
            if event_time:
                # Convert ISO format to timestamp
                dt = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
                timestamp = dt.timestamp()
                
                # Format times
                pacific_time = format_timestamp(timestamp, 'America/Los_Angeles')
                utc_time = format_timestamp(timestamp, 'UTC')
                
                table.add_row(
                    event['summary'],
                    pacific_time,
                    utc_time,
                    "[green]✓ Synced[/green]"
                )

    console.print(f"\n[bold]Calendar Sync Results[/bold]")
    console.print(table)
    console.print(f"\nSuccessfully synced [green]{len(synced_events)}[/green] events to calendar\n")

if __name__ == "__main__":
    main()