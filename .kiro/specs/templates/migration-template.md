# Migration Spec Template

## Migration Goal
<!-- What is being migrated? (DB, framework, service, etc.) -->

## Current State
<!-- Current technology/version/architecture -->

## Target State
<!-- Target technology/version/architecture -->

## Risk Assessment
- Data loss risk: <!-- low/medium/high -->
- Downtime required: <!-- yes/no, estimated duration -->
- Rollback plan: <!-- How to revert if things go wrong -->

## Tasks
- [ ] Audit current usage and dependencies
- [ ] Create migration plan with rollback steps
- [ ] Set up target environment
- [ ] Write migration scripts
- [ ] Test migration on staging/copy
- [ ] Execute migration
- [ ] Verify all systems operational
- [ ] Monitor for 24-48h post-migration
