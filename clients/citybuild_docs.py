"""City Build document checklist (metadata only — no blob calls)."""

# Checklist applies to Academy only — not CAPSA.
CITYBUILD_PROGRAMS = frozenset({'citybuild'})

# (panel_title, items) where each item is (doc_type_code | None, label, source)
# source: document | resume | casenotes
CITYBUILD_CHECKLIST_PANELS = (
    (
        'Panel 1 — Intake & identification',
        (
            ('cb_application', 'Application (photo release embedded)', 'document'),
            ('cb_roi', 'Release of Information', 'document'),
            ('cb_tabe', 'TABE', 'document'),
            ('cb_parq', 'Par-Q (doc clearance if required)', 'document'),
            ('cb_iep', 'IEP', 'document'),
            ('id', 'DL', 'document'),
            ('cb_ssn_card', 'SS card', 'document'),
            ('sf_residency', 'Domicile', 'document'),
            ('hs_diploma', 'HSD / GED', 'document'),
            ('cb_drug_test', 'DT', 'document'),
            ('cb_safety', 'Safety Form', 'document'),
            ('cb_covid_vax', 'COVID vax', 'document'),
            ('cb_po', 'PO', 'document'),
        ),
    ),
    (
        'Panel 2 — BESI',
        (
            ('cb_besi', 'BESI (ensure complete)', 'document'),
        ),
    ),
    (
        'Panel 3 — Evaluations & notes',
        (
            ('reference', 'Letter of recommendation', 'document'),
            ('cb_jrt_eval', 'JRT eval', 'document'),
            (None, 'Case notes', 'casenotes'),
        ),
    ),
    (
        'Panel 4 — Agreements',
        (
            ('cb_rights', 'Rights & Responsibilities', 'document'),
            ('cb_lou', 'Letter of Understanding & Agreement', 'document'),
        ),
    ),
    (
        'Panel 5 — Employment readiness',
        (
            ('resume', 'Resume', 'resume'),
            ('cb_interview', 'Interview sheet', 'document'),
            ('cb_emp_edu_verify', 'Employment & Education Verification', 'document'),
            ('cb_support_svc', 'Supportive Service Determination', 'document'),
        ),
    ),
)

# Doc types shown in CityBuild hub upload dropdown (general types still useful).
CITYBUILD_UPLOAD_DOC_TYPES = (
    ('cb_application', 'Application (photo release embedded)'),
    ('cb_roi', 'Release of Information'),
    ('cb_tabe', 'TABE'),
    ('cb_parq', 'Par-Q (doc clearance if required)'),
    ('cb_iep', 'IEP'),
    ('id', 'DL / Government ID'),
    ('cb_ssn_card', 'SS card'),
    ('sf_residency', 'Domicile / Proof of SF Residency'),
    ('hs_diploma', 'HSD / GED'),
    ('cb_drug_test', 'DT'),
    ('cb_safety', 'Safety Form'),
    ('cb_covid_vax', 'COVID vax'),
    ('cb_po', 'PO'),
    ('cb_besi', 'BESI'),
    ('reference', 'Letter of recommendation'),
    ('cb_jrt_eval', 'JRT eval'),
    ('cb_rights', 'Rights & Responsibilities'),
    ('cb_lou', 'Letter of Understanding & Agreement'),
    ('cb_interview', 'Interview sheet'),
    ('cb_emp_edu_verify', 'Employment & Education Verification'),
    ('cb_support_svc', 'Supportive Service Determination'),
    ('intake', 'Intake Form'),
    ('consent', 'Consent Form'),
    ('photo_release', 'Photo Release'),
    ('other', 'Other Document'),
)


def is_citybuild_client(client):
    return bool(client and client.training_interest in CITYBUILD_PROGRAMS)


def iter_citybuild_checklist_items():
    for panel_title, items in CITYBUILD_CHECKLIST_PANELS:
        for code, label, source in items:
            yield panel_title, code, label, source


# Fixed checklist used by reports (K = 22 items, constant).
CITYBUILD_CHECKLIST_ITEMS = tuple(iter_citybuild_checklist_items())
CITYBUILD_CHECKLIST_ITEM_COUNT = len(CITYBUILD_CHECKLIST_ITEMS)

# Valid doc_type codes used by checklist tile uploads (server-side guard).
CITYBUILD_CHECKLIST_DOC_TYPES = frozenset(
    code for _panel, code, _label, source in CITYBUILD_CHECKLIST_ITEMS
    if source == 'document' and code
)


def checklist_label_for_doc_type(doc_type):
    for _panel, code, label, source in CITYBUILD_CHECKLIST_ITEMS:
        if source == 'document' and code == doc_type:
            return label
    return doc_type.replace('_', ' ').title()


def citybuild_item_present(code, source, present_doc_types, has_resume, case_notes_count):
    if source == 'resume':
        return has_resume
    if source == 'casenotes':
        return case_notes_count > 0
    return code in present_doc_types


def present_doc_types_for_client(client):
    """Doc types on file for one client (DB only, no blob calls)."""
    present = set(client.documents.exclude(file='').values_list('doc_type', flat=True))
    if client.resume or 'resume' in present:
        present.add('resume')
    return present


def citybuild_packet_for_client(client, casenotes_count=None):
    """Checklist score for one CityBuild client."""
    if casenotes_count is None:
        casenotes_count = getattr(client, 'casenotes_count', None)
    if casenotes_count is None:
        casenotes_count = client.casenotes.count()
    present = present_doc_types_for_client(client)
    return evaluate_citybuild_packet(
        present,
        'resume' in present,
        casenotes_count,
    )


def evaluate_citybuild_packet(present_doc_types, has_resume, case_notes_count):
    """
    Score one client against the CityBuild checklist.

    Time: O(K) with K = CITYBUILD_CHECKLIST_ITEM_COUNT (fixed ~22, not client count).
    Space: O(K) for the per-item status list.
    """
    items = []
    missing_labels = []
    on_file = 0
    for _panel, code, label, source in CITYBUILD_CHECKLIST_ITEMS:
        present = citybuild_item_present(
            code, source, present_doc_types, has_resume, case_notes_count,
        )
        items.append((label, present))
        if present:
            on_file += 1
        else:
            missing_labels.append(label)
    total = CITYBUILD_CHECKLIST_ITEM_COUNT
    return {
        'on_file': on_file,
        'total': total,
        'missing_count': total - on_file,
        'missing_labels': missing_labels,
        'items': items,
    }
