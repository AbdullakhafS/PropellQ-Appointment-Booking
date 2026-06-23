import type { ProfileIntake } from '../types/profileIntake';

/**
 * Exports the intake as a print-friendly page using the browser's built-in print dialog.
 * Falls back gracefully if jsPDF is not available — uses window.print() instead.
 *
 * The function:
 * 1. Builds a compact HTML string for the intake.
 * 2. Opens a hidden iframe, writes the HTML into it, and calls print().
 * 3. Removes the iframe after printing.
 */
export function exportIntakePdf(intake: ProfileIntake): void {
  const modeLabel = intake.mode === 'ai' ? 'AI Chatbot' : 'Manual Form';
  const completedDate = new Date(intake.completedAt).toLocaleString();

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Patient Intake – ${completedDate}</title>
  <style>
    body { font-family: Arial, sans-serif; font-size: 11pt; color: #000; margin: 2cm; }
    h1 { font-size: 16pt; margin-bottom: 4pt; }
    h2 { font-size: 12pt; margin: 14pt 0 4pt; border-bottom: 1px solid #ccc; padding-bottom: 2pt; }
    p, li { margin: 2pt 0; line-height: 1.4; }
    table { border-collapse: collapse; width: 100%; margin-top: 4pt; }
    th, td { border: 1px solid #ccc; padding: 4pt 6pt; text-align: left; }
    th { background: #f0f0f0; font-weight: bold; }
    .meta { font-size: 9pt; color: #555; margin-bottom: 8pt; }
    .badge { display: inline-block; padding: 1pt 4pt; border: 1px solid #999; border-radius: 3pt; font-size: 9pt; }
    ul { padding-left: 16pt; }
    @media print { body { margin: 1cm; } }
  </style>
</head>
<body>
  <h1>Patient Intake Summary</h1>
  <p class="meta">
    Completed: ${completedDate} &bull;
    Via: ${modeLabel} &bull;
    Patient #${intake.patientId} &bull;
    Appointment #${intake.appointmentId}
  </p>

  <h2>Chief Complaint</h2>
  <p>${intake.chiefComplaint ? escapeHtml(intake.chiefComplaint) : '<em>Not provided</em>'}</p>

  <h2>Medical History</h2>
  ${intake.medicalHistory.length === 0
    ? '<p><em>None reported</em></p>'
    : `<ul>${intake.medicalHistory.map(h =>
        `<li><strong>${escapeHtml(h.conditionName)}</strong>${h.conditionCode ? ` [${escapeHtml(h.conditionCode)}]` : ''} — ${h.conditionStatus}</li>`
      ).join('')}</ul>`}

  <h2>Medications</h2>
  ${intake.medications.length === 0
    ? '<p><em>None reported</em></p>'
    : `<table>
        <thead><tr><th>Medication</th><th>Dosage</th><th>Frequency</th><th>Route</th></tr></thead>
        <tbody>${intake.medications.map(m =>
          `<tr>
            <td>${escapeHtml(m.medicationName)}</td>
            <td>${escapeHtml(m.dosage ?? '—')}</td>
            <td>${escapeHtml(m.frequency ?? '—')}</td>
            <td>${escapeHtml(m.route ?? '—')}</td>
          </tr>`
        ).join('')}</tbody>
      </table>`}

  <h2>Allergies</h2>
  ${intake.allergies.length === 0
    ? '<p><em>None reported</em></p>'
    : `<table>
        <thead><tr><th>Allergen</th><th>Type</th><th>Reaction</th><th>Severity</th><th>Description</th></tr></thead>
        <tbody>${intake.allergies.map(a =>
          `<tr>
            <td>${escapeHtml(a.allergenName)}</td>
            <td>${escapeHtml(a.allergenType)}</td>
            <td>${a.reactionType === 'allergic' ? 'Drug Allergy' : 'Side Effect'}</td>
            <td>${escapeHtml(a.severity ?? '—')}</td>
            <td>${escapeHtml(a.reactionDescription ?? '—')}</td>
          </tr>`
        ).join('')}</tbody>
      </table>`}

  <h2>Insurance</h2>
  ${!intake.insurance
    ? '<p><em>Not provided</em></p>'
    : `<ul>
        <li><strong>Plan:</strong> ${escapeHtml(intake.insurance.insuranceName ?? '—')}</li>
        <li><strong>Member ID:</strong> ${escapeHtml(intake.insurance.memberId ?? '—')}</li>
        ${intake.insurance.groupNumber ? `<li><strong>Group:</strong> ${escapeHtml(intake.insurance.groupNumber)}</li>` : ''}
        ${intake.insurance.planName ? `<li><strong>Plan Type:</strong> ${escapeHtml(intake.insurance.planName)}</li>` : ''}
        ${intake.insurance.verificationStatus
          ? `<li><strong>Status:</strong> <span class="badge">${escapeHtml(intake.insurance.verificationStatus)}</span></li>`
          : ''}
      </ul>`}
</body>
</html>`;

  const iframe = document.createElement('iframe');
  iframe.style.cssText = 'position:fixed;top:-9999px;left:-9999px;width:1px;height:1px;';
  document.body.appendChild(iframe);

  const doc = iframe.contentDocument ?? iframe.contentWindow?.document;
  if (!doc) {
    document.body.removeChild(iframe);
    return;
  }

  doc.open();
  doc.write(html);
  doc.close();

  iframe.contentWindow?.focus();
  iframe.contentWindow?.print();

  setTimeout(() => {
    document.body.removeChild(iframe);
  }, 2000);
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
