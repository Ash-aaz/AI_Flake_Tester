import pytest
from calculations import validate_json, model_efficiency, calculate_percentiles
from config import Logs, Memo, Breach, Report
from pydantic import TypeAdapter

def test_validate_json_easy_ideal():
    ideal_output = ['{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}, {"server": "Beta-Node", "downtime_minutes": 15, "critical": false}]}']
    assert validate_json(ideal_output, TypeAdapter(Logs)) == 0

false_cases_easy = (['[{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}]'], ['{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": "90", "critical": true}]}'], 
                    ['{"incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}'], ['Here is the server incident log: {"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}'], 
                    ['```json\n{"log_id": "REP-9981", "incidents": [{"server": "Alpha-Node", "downtime_minutes": 90, "critical": true}]}\n```'])

@pytest.mark.parametrize("incorrect_output", false_cases_easy)
def test_validate_json_easy_false(incorrect_output):
    assert validate_json(incorrect_output, TypeAdapter(Logs)) == 1

def test_validate_json_med_ideal():
    ideal_output = ['{"project_id": "NOVA-7", "status": "active", "budget_remaining": 40000.0, "team": [{"member_id": "ENG-101", "role": "backend", "is_lead": true}, {"member_id": "ENG-204", "role": "frontend", "is_lead": false}, {"member_id": "ENG-309", "role": "QA", "is_lead": false}], "milestones": [{"title": "API Integration", "completed": true, "blockers": []}, {"title": "UI Overhaul", "completed": false, "blockers": ["design sign-off", "pending assets from client"]}, {"title": "Load Testing", "completed": false, "blockers": []}]}']
    assert validate_json(ideal_output, TypeAdapter(Memo)) == 0

false_cases_med = (
    ['{"project_id": "NOVA-7", "status": "in_progress", "budget_remaining": 40000.0, "team": [{"member_id": "ENG-101", "role": "backend", "is_lead": true}], "milestones": [{"title": "API Integration", "completed": true, "blockers": []}]}'],
    ['{"project_id": "NOVA-7", "status": "active", "budget_remaining": "forty thousand", "team": [{"member_id": "ENG-101", "role": "backend", "is_lead": true}], "milestones": [{"title": "API Integration", "completed": true, "blockers": []}]}'],
    ['{"project_id": "NOVA-7", "status": "active", "budget_remaining": 40000.0, "team": [{"member_id": "ENG-101", "role": "backend", "is_lead": "true"}], "milestones": [{"title": "API Integration", "completed": true, "blockers": []}]}'],
    ['{"project_id": "NOVA-7", "status": "active", "budget_remaining": 40000.0, "team": [{"member_id": "ENG-101", "role": "backend", "is_lead": true}], "milestones": [{"title": "UI Overhaul", "completed": false, "blockers": null}]}'],
    ['{"status": "active", "budget_remaining": 40000.0, "team": [{"member_id": "ENG-101", "role": "backend", "is_lead": true}], "milestones": [{"title": "API Integration", "completed": true, "blockers": []}]}'],
    ['```json\n{"project_id": "NOVA-7", "status": "active", "budget_remaining": 40000.0, "team": [{"member_id": "ENG-101", "role": "backend", "is_lead": true}], "milestones": [{"title": "API Integration", "completed": true, "blockers": []}]}\n```'],
    )

@pytest.mark.parametrize("incorrect_output", false_cases_med)
def test_validate_json_med_false(incorrect_output):
    assert validate_json(incorrect_output, TypeAdapter(Memo)) == 1

def test_validate_json_hard_ideal():
    ideal_output = ['{"incident_id": "INC-4471", "severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}, {"system_name": "Web-App", "compromised": true, "recovery_status": "degraded"}, {"system_name": "Backup-Node", "compromised": true, "recovery_status": "operational"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}, {"responder_id": "SEC-02", "role": "forensics", "is_lead": false}, {"responder_id": "SEC-03", "role": "communications", "is_lead": false}, {"responder_id": "SEC-04", "role": "containment", "is_lead": false}], "estimated_data_loss_gb": null, "first_detected": null}']
    assert validate_json(ideal_output, TypeAdapter(Breach)) == 0

false_cases_hard = (
    ['{"incident_id": "INC-4471", "severity": "serious", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}], "estimated_data_loss_gb": null, "first_detected": null}'],
    ['{"incident_id": "INC-4471", "severity": "high", "attack_type": "hacking", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}], "estimated_data_loss_gb": null, "first_detected": null}'],
    ['{"incident_id": "INC-4471", "severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "damaged"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}], "estimated_data_loss_gb": null, "first_detected": null}'],
    ['{"incident_id": "INC-4471", "severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "team_lead", "is_lead": true}], "estimated_data_loss_gb": null, "first_detected": null}'],
    ['{"incident_id": "INC-4471", "severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}], "estimated_data_loss_gb": "unknown", "first_detected": null}'],
    ['{"incident_id": "INC-4471", "severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}], "estimated_data_loss_gb": null, "first_detected": "late Tuesday"}'],
    ['{"incident_id": "INC-4471", "severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": "true"}], "estimated_data_loss_gb": null, "first_detected": null}'],
    ['{"severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}], "estimated_data_loss_gb": null, "first_detected": null}'],
    ['```json\n{"incident_id": "INC-4471", "severity": "high", "attack_type": "unauthorised_access", "contained": false, "affected_systems": [{"system_name": "DB-Primary", "compromised": true, "recovery_status": "offline"}], "responders": [{"responder_id": "SEC-01", "role": "incident_lead", "is_lead": true}], "estimated_data_loss_gb": null, "first_detected": null}\n```'],
)

@pytest.mark.parametrize("incorrect_output", false_cases_hard)
def test_validate_json_hard_false(incorrect_output):
    assert validate_json(incorrect_output, TypeAdapter(Breach)) == 1


def test_validate_json_ultra_ideal():
    ideal_output = ['{"report_id": "REP-2291", "severity": "severe", "outcome": "ongoing", "patient": {"age": 67, "sex": "male", "pre_existing_conditions": ["hypertension", "type 2 diabetes"]}, "events": [{"event_type": "tachycardia", "onset_day": 3, "duration_hours": null, "causality": "probable", "interventions": [{"intervention_type": "medication", "description": "IV metoprolol", "effective": null}, {"intervention_type": "monitoring", "description": "continuous cardiac monitoring", "effective": null}]}, {"event_type": "skin rash", "onset_day": 5, "duration_hours": 24, "causality": "possible", "interventions": [{"intervention_type": "medication", "description": "topical treatment", "effective": true}]}], "reported_by": {"role": "physician", "institution_type": "hospital"}}']
    assert validate_json(ideal_output, TypeAdapter(Report)) == 0

false_cases_ultra = (
    ['{"report_id": "REP-2291", "severity": "high", "outcome": "ongoing", "patient": {"age": 67, "sex": "male", "pre_existing_conditions": ["hypertension", "type 2 diabetes"]}, "events": [{"event_type": "tachycardia", "onset_day": 3, "duration_hours": null, "causality": "probable", "interventions": [{"intervention_type": "medication", "description": "IV metoprolol", "effective": null}]}], "reported_by": {"role": "physician", "institution_type": "hospital"}}'],
    ['{"report_id": "REP-2291", "severity": "severe", "outcome": "ongoing", "patient": {"age": 67, "sex": "male", "pre_existing_conditions": ["hypertension", "type 2 diabetes"]}, "events": [{"event_type": "tachycardia", "onset_day": 3, "causality": "probable", "interventions": [{"intervention_type": "medication", "description": "IV metoprolol", "effective": null}]}], "reported_by": {"role": "physician", "institution_type": "hospital"}}'],
    ['{"report_id": "REP-2291", "severity": "severe", "outcome": "ongoing", "patient": {"age": 67, "sex": "male", "pre_existing_conditions": ["hypertension", "type 2 diabetes"]}, "events": [{"event_type": "tachycardia", "onset_day": 3, "duration_hours": null, "causality": "certain", "interventions": [{"intervention_type": "medication", "description": "IV metoprolol", "effective": null}]}], "reported_by": {"role": "physician", "institution_type": "hospital"}}'],
    ['{"report_id": "REP-2291", "severity": "severe", "outcome": "ongoing", "patient": {"age": 67, "sex": "male", "pre_existing_conditions": ["hypertension", "type 2 diabetes"]}, "events": [{"event_type": "tachycardia", "onset_day": 3, "duration_hours": null, "causality": "probable", "interventions": [{"intervention_type": "surgery", "description": "IV metoprolol", "effective": null}]}], "reported_by": {"role": "physician", "institution_type": "hospital"}}'],
    ['{"report_id": "REP-2291", "severity": "severe", "outcome": "ongoing", "patient": {"age": 67, "sex": "male", "pre_existing_conditions": ["hypertension", "type 2 diabetes"]}, "events": [{"event_type": "tachycardia", "onset_day": 3, "duration_hours": null, "causality": "probable", "interventions": [{"intervention_type": "medication", "description": "IV metoprolol"}]}], "reported_by": {"role": "physician", "institution_type": "hospital"}}'],
    ['```json\n{"report_id": "REP-2291", "severity": "severe", "outcome": "ongoing", "patient": {"age": 67, "sex": "male", "pre_existing_conditions": []}, "events": [{"event_type": "tachycardia", "onset_day": 3, "duration_hours": null, "causality": "probable", "interventions": [{"intervention_type": "medication", "description": "IV metoprolol", "effective": null}]}], "reported_by": {"role": "physician", "institution_type": "hospital"}}\n```'],
)

@pytest.mark.parametrize("incorrect_output", false_cases_ultra)
def test_validate_json_ultra_false(incorrect_output):
    assert validate_json(incorrect_output, TypeAdapter(Report)) == 1

def test_model_efficiency():
    duration_values = [2000000000, 3000000000, 2000000000, 1000000000, 0]
    count_values = [100, 150, 120, 80, 0]

    assert model_efficiency(duration_values, count_values) == pytest.approx(60.0)

def test_calculate_percentiles_insufficient_data():
    dummy_list = list(range(99))
    assert calculate_percentiles(dummy_list) == (None, None)

def test_calculate_percentiles_upper_bound():
    dummy_durations = [x*(10**9) for x in range(1,101)]
    assert calculate_percentiles(dummy_durations) == (pytest.approx(95.95), pytest.approx(99.99))
