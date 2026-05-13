const INDIAN_PHONE_REGEX = /(?:\+91[\s-]?)?[6-9]\d{9}\b/g;
const EMAIL_REGEX = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;

export function toSentenceCase(value = '') {
  return String(value)
    .toLowerCase()
    .split('_')
    .join(' ')
    .replace(/(^\w|\s\w)/g, (char) => char.toUpperCase());
}

export function formatMoney(value) {
  if (!value) return 'Not detected';
  return value;
}

export function deriveRecommendation(tenderData, evaluations) {
  if (!tenderData) {
    return {
      label: 'Awaiting Bundle',
      tone: 'slate',
      summary: 'Upload a tender bundle to generate a defensible briefing.',
    };
  }

  if (!evaluations || Object.keys(evaluations).length === 0) {
    return {
      label: 'Ready For Bidder Evaluation',
      tone: 'blue',
      summary: `${tenderData.criteria?.length || 0} eligibility criteria extracted from ${tenderData.bundle_documents?.length || 1} source document(s).`,
    };
  }

  const allEvaluations = Object.values(evaluations);
  const eligible = allEvaluations.filter((ev) => ev.overall_status === 'ELIGIBLE').length;
  const review = allEvaluations.filter((ev) => ev.overall_status === 'MANUAL_REVIEW').length;
  const rejected = allEvaluations.filter((ev) => ev.overall_status === 'NOT_ELIGIBLE').length;

  if (eligible > 0 && review === 0) {
    return {
      label: 'Publishable',
      tone: 'green',
      summary: `${eligible} bidder(s) cleared evaluation with no unresolved review blockers.`,
    };
  }

  if (review > 0) {
    return {
      label: 'Operator Review Required',
      tone: 'amber',
      summary: `${review} bidder(s) still have ambiguous or manual-review criteria before final publication.`,
    };
  }

  return {
    label: 'Decision Ready',
    tone: 'red',
    summary: `${rejected} bidder(s) failed mandatory requirements. Publish or seek clarification with officer sign-off.`,
  };
}

export function buildQueueItems(tenderData, evaluations) {
  const recommendation = deriveRecommendation(tenderData, evaluations);
  const liveItem = tenderData
    ? {
        id: tenderData.tender_id,
        title: tenderData.metadata?.title || tenderData.filename || 'Active Tender Bundle',
        authority: tenderData.metadata?.authority || 'Government Procurement Authority',
        deadline: tenderData.metadata?.closing_date || 'Pending extraction',
        state: recommendation.label.toUpperCase(),
        source: tenderData.metadata?.portal || 'Upload bundle',
        urgent: !evaluations,
      }
    : null;

  const seeded = [
    {
      id: 'TS/SEED/001',
      title: 'Border Outpost Surveillance Systems',
      authority: 'CRPF Procurement Cell',
      deadline: '16 May 2026',
      state: 'ACTION',
      source: 'GeM',
      urgent: true,
    },
    {
      id: 'TS/SEED/002',
      title: 'Portable Power Backup Modules',
      authority: 'Indian Railways',
      deadline: '21 May 2026',
      state: 'READY',
      source: 'Upload',
      urgent: false,
    },
    {
      id: 'TS/SEED/003',
      title: 'Perimeter Monitoring Equipment',
      authority: 'State Police HQ',
      deadline: '29 May 2026',
      state: 'WAITING',
      source: 'DefProc',
      urgent: false,
    },
  ];

  return liveItem ? [liveItem, ...seeded] : seeded;
}

export function buildSourceAdapters(tenderData) {
  const bundleCount = tenderData?.bundle_documents?.length || 0;
  return [
    {
      name: 'GeM',
      status: 'Healthy',
      tone: 'green',
      note: 'Discovery adapter available for operator-triggered imports.',
      fetches: bundleCount ? 1 : 0,
      mode: 'Configured',
    },
    {
      name: 'DefProc',
      status: 'Pilot',
      tone: 'amber',
      note: 'Public discovery flows can be demonstrated as assisted import.',
      fetches: 0,
      mode: 'Operator-assisted',
    },
    {
      name: 'Uploads',
      status: 'Always On',
      tone: 'blue',
      note: `${bundleCount} tender document(s) currently attached to the active workspace.`,
      fetches: bundleCount,
      mode: 'Local',
    },
  ];
}

export function extractContactsFromText(text = '') {
  const emails = Array.from(new Set((text.match(EMAIL_REGEX) || []).map((value) => value.trim())));
  const phones = Array.from(
    new Set(
      (text.match(INDIAN_PHONE_REGEX) || []).map((value) =>
        value.replace(/\s+/g, '').replace(/-+/g, '')
      )
    )
  );

  return {
    emails,
    phones,
  };
}

export function verdictToMatrixStatus(verdict) {
  if (!verdict) return { label: 'UNKNOWN', tone: 'slate' };
  const confidence = Number(verdict.confidence || 0);

  if (verdict.status === 'ELIGIBLE' && confidence >= 0.85) {
    return { label: 'VERIFIED', tone: 'green' };
  }
  if (verdict.status === 'ELIGIBLE') {
    return { label: 'PARTIAL', tone: 'blue' };
  }
  if (verdict.status === 'MANUAL_REVIEW') {
    return { label: 'AMBIGUOUS', tone: 'amber' };
  }
  return { label: 'MISSING', tone: 'red' };
}

export function buildTenderAmbiguities(criteria = [], evaluations = {}) {
  return criteria
    .map((criterion) => {
      const flagged = Object.entries(evaluations)
        .map(([bidder, evaluation]) => {
          const verdict = evaluation.verdicts?.find((item) => item.criterion_id === criterion.id);
          if (!verdict) return null;
          if (verdict.status === 'MANUAL_REVIEW' || Number(verdict.confidence || 0) < 0.65) {
            return {
              bidder,
              status: verdict.status,
              reasoning: verdict.reasoning,
            };
          }
          return null;
        })
        .filter(Boolean);

      if (!flagged.length) return null;
      return {
        criterionId: criterion.id,
        criterionText: criterion.text,
        flagged,
      };
    })
    .filter(Boolean);
}

export function buildClarificationMessage(bidderName, evaluation) {
  const gaps = (evaluation?.verdicts || [])
    .filter((verdict) => verdict.status !== 'ELIGIBLE')
    .slice(0, 4)
    .map((verdict) => `- ${verdict.criterion_id}: ${verdict.criterion_text || verdict.reasoning}`);

  return [
    `Subject: Clarification required for ${bidderName}`,
    '',
    `Dear ${bidderName},`,
    '',
    'TenderSight flagged the following items for clarification before final decision publication:',
    ...gaps,
    '',
    'Please provide supporting documents or written clarification against the listed criteria.',
    '',
    'Regards,',
    'Procurement Evaluation Cell',
  ].join('\n');
}

export function buildPublishMessage(bidderName, evaluation) {
  const outcome = toSentenceCase(evaluation?.overall_status || 'MANUAL_REVIEW');
  return [
    `Subject: Tender evaluation outcome for ${bidderName}`,
    '',
    `Dear ${bidderName},`,
    '',
    `Your submission has been marked: ${outcome}.`,
    '',
    'Please contact the issuing authority if you require formal clarification or supporting remarks.',
    '',
    'Regards,',
    'TenderSight Operator Desk',
  ].join('\n');
}
