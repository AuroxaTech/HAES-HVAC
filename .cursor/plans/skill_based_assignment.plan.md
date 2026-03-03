# Skill-Based Technician Assignment — Implemented

## Summary

Job assignment and availability now consider technician skills from Odoo (HR Skills). Only technicians who have the required skills for the job are used for slot search and assignment.

---

## Implemented

### 1. Odoo: fetch technician skills (`src/integrations/odoo_appointments.py`)

- **`get_technician_skills(employee_ids)`**  
  - Reads `hr.employee.skill` for the given `hr.employee` IDs.  
  - Returns `{employee_id: [{"skill_name": str, "skill_type": str, "level": str}]}`.  
  - If the model is missing or the call fails, returns `{}` so callers treat it as “no skill filter”.

### 2. Job → required skills (`src/brains/ops/skill_mapping.py`)

- **`SERVICE_TYPE_REQUIRED_SKILLS`**  
  - Maps each service type code to a list of required skill names (e.g. `"Electrical Diagnostics"`, `"Low Voltage Troubleshooting"`).
- **`DESCRIPTION_SKILL_HINTS`**  
  - Adds skills from description (e.g. “heat pump” → `"Heat Pump"`).
- **`get_required_skills_for_service(service_type, description)`**  
  - Returns the list of required skill names for a given service type and optional description.
- **`technician_has_required_skills(skill_list, required_skills)`**  
  - Returns whether the technician has all required skills (case-insensitive).
- **`filter_technicians_by_skills(technicians, skills_by_employee_id, required_skills)`**  
  - Returns only technicians who have all required skills; if `required_skills` is empty, returns all.

### 3. Check availability (`src/vapi/tools/ops/check_availability.py`)

- After `get_live_technicians()`, computes `required_skills` from `get_required_skills_for_service(service_type, ...)`.
- If `required_skills` is non-empty: fetches skills via `get_technician_skills(employee_ids)`, then filters with `filter_technicians_by_skills`.
- If no technician has the required skills, falls back to using all technicians and logs.
- Slot search and response shape unchanged.

### 4. OPS handlers (`src/brains/ops/handlers.py`)

- **`_candidate_technicians(..., required_skills=None)`**  
  - When `required_skills` is set, fetches skills and returns only technicians who have all required skills.
- **`_find_best_technician_slots(..., required_skills=None)`** and **`_find_available_technician_for_requested_start(..., required_skills=None)`**  
  - Pass `required_skills` through to `_candidate_technicians`.
- **Schedule flow**  
  - Computes `required_skills` from `get_required_skills_for_service(service_type, problem_desc)` and passes it into all slot/technician lookups.
- **Service request flow**  
  - Computes `required_skills_sr` and passes it to `_find_best_technician_slots`.
- **Reschedule flow**  
  - Computes `required_skills_reschedule` from description and passes it to technician/slot lookups.

### 5. Tests

- **`tests/test_skill_mapping.py`**  
  - Unit tests for `get_required_skills_for_service`, `technician_has_required_skills`, and `filter_technicians_by_skills`.
- **`tests/test_vapi_tools/test_ops_tools.py`**  
  - All 24 OPS tool tests (including 6 `check_availability` tests) pass; when mocks don’t provide `employee_id`, skill filter is skipped and behavior is unchanged.

---

## Odoo dependency

- **Model:** `hr.employee.skill` (Odoo HR Skills / `hr_skills` or `hr_employee_skill`).
- If the model is not installed or the API call fails, the code logs a warning and proceeds without skill filtering (all technicians are considered).

---

## Configuration

- Edit **`src/brains/ops/skill_mapping.py`** to change:
  - `SERVICE_TYPE_REQUIRED_SKILLS`: required skills per service type.
  - `DESCRIPTION_SKILL_HINTS`: description keywords and extra skills (e.g. equipment types).
- Skill names must match the names stored in Odoo (e.g. `"Electrical Diagnostics"`, `"Heat Pump"`, `"Low Voltage Troubleshooting"`).
