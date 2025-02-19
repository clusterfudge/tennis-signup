#!/usr/bin/env python3
import cal
import storage
import os
import argparse
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

def force_sync_events(db: storage.Storage, plan: dict, calendar_id: str) -> list:
    """Remove all existing events and recreate them"""
    console = Console()
    synced_events = []
    
    # First remove all existing calendar events
    for slug, inst in plan.items():
        token, existing_event = cal.get_event_for_class(db, inst, calendar_id)
        if existing_event:
            try:
                cal.remove_calendar_event(db, inst, calendar_id)
                console.print(f"[yellow]Removed existing event: {existing_event.get('summary')}[/yellow]")
            except Exception as e:
                console.print(f"[red]Error removing event {existing_event.get('summary')}: {str(e)}[/red]")
    
    # Now create all events fresh
    for slug, inst in plan.items():
        event = cal.create_event_for_class(db, inst, calendar_id)
        if event:
            synced_events.append(event)
    
    return synced_events

def main():
    parser = argparse.ArgumentParser(description='Sync calendar events')
    parser.add_argument('--force', action='store_true', 
                      help='Force remove and re-add all calendar entries')
    args = parser.parse_args()

    console = Console()
    
    # Initialize the storage
    db = storage.Storage('./storage')
    
    # Get the latest plan
    _, plan = db.latest('plan')
    calendar_id = os.environ.get('SHARED_CALENDAR_ID')
    
    if not plan:
        console.print("[red]No plan found to sync[/red]")
        return

    if not calendar_id:
        console.print("[red]No SHARED_CALENDAR_ID found in environment variables[/red]")
        return

    # Create table for output
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Event Title")
    table.add_column("Pacific Time")
    table.add_column("UTC")
    table.add_column("Status")

    # Sync the plan to calendar
    if args.force:
        console.print("[yellow]Force sync requested - removing and re-adding all events...[/yellow]")
        synced_events = force_sync_events(db, plan, calendar_id)
    else:
        synced_events = cal.sync_plan_to_calendar(db, plan, calendar_id)
    
    if not synced_events:
        console.print("[yellow]No events were synced[/yellow]")
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
                
                status = "[green]✓ Synced[/green]" if not args.force else "[yellow]↻ Re-synced[/yellow]"
                table.add_row(
                    event['summary'],
                    pacific_time,
                    utc_time,
                    status
                )

    console.print(f"\n[bold]Calendar Sync Results[/bold]")
    console.print(table)
    console.print(f"\nSuccessfully {'re-' if args.force else ''}synced [green]{len(synced_events)}[/green] events to calendar\n")

if __name__ == "__main__":
    main()