#!/usr/bin/env bats
# ha_backup_config.sh: timestamped tarball of HA YAML in /share/wayne-backups (no secrets).

SCRIPT="$BATS_TEST_DIRNAME/../../infrastructure/ha/ha_backup_config.sh"

@test "dry-run prints a timestamped tarball under /share/wayne-backups" {
  run "$SCRIPT" --dry-run
  [ "$status" -eq 0 ]
  [[ "$output" =~ /share/wayne-backups/config-[0-9]{8}-[0-9]{6}\.tar\.gz ]]
}

@test "backup covers the YAML we deploy" {
  run "$SCRIPT" --dry-run
  for p in configuration.yaml includes custom_sentences packages themes dashboards esphome; do
    [[ "$output" == *"$p"* ]]
  done
}

@test "backup never includes secrets" {
  run "$SCRIPT" --dry-run
  [[ "$output" == *"--exclude=secrets.yaml"* ]]
  [[ "$output" == *"--exclude=esphome/secrets.yaml"* ]]
}
