# Status: alpha
Supports booking a class, within 4 seconds. Unlikely that there's a need to improve there.
Scheduled via cron, running on a raspberry pi. Not ideal, should be migrated to a managed service.

# Future Plans
Weekly: send out a proposed schedule, allow adjustments. 
Something like "on friday, plan for next monday - saturday"
Default classes on no action
 - at a later time schedule is generated from default if none exists
 - need some UX to update schedule -- chat bot? web app? 

What is a schedule?
A list of classes to book in week starting DATE
cron every 15 minutes?

this is going to need a database -- possibly time to reconsider litestream 