# lit.ubuntu.automatic_updates

Configure weekly automatic OS updates on Ubuntu systems via cron. By default it
runs `apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y upgrade` every
Sunday at 06:00 and writes output to `/var/log/apt-auto-weekly.log`.

## Variables

- `automatic_updates_enabled` (bool, default: `true`): Enable or disable the cron job.
- `automatic_updates_minute` (string, default: `"0"`): Cron minute.
- `automatic_updates_hour` (string, default: `"6"`): Cron hour.
- `automatic_updates_weekday` (string, default: `"0"`): Cron weekday.
- `automatic_updates_user` (string, default: `"root"`): User owning the cron entry.
- `automatic_updates_log_file` (string, default: `"/var/log/apt-auto-weekly.log"`): Log destination.
- `automatic_updates_command` (string): Command to run.
- `automatic_updates_cron_name` (string, default: `"Weekly automatic updates"`): Cron entry name.
- `automatic_updates_initial_update` (bool, default: `true`): Run an initial apt upgrade when the role executes.
