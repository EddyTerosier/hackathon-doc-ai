import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-hot-toast";

import { authStorage } from "../auth/authStorage";
import {
  createCompany,
  createSupplier,
  getCompanies,
  getDocumentDetail,
  getDocumentGroups,
  getSuppliers,
} from "../api/dashboardApi";

function formatDate(value, fallback = "Not processed yet") {
  if (!value) return fallback;

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return fallback;

  return date.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getQueueTone(group) {
  if ((group.documents || []).some((document) => document.analysis_status === "failed")) return "bad";
  if (group.state === "non_compliant" || group.validation_result === "invalid") return "bad";
  if (group.state === "compliant" || group.validation_result === "valid") return "ok";
  if (group.status === "processing" || group.validation_result === "pending") return "warn";
  return "neutral";
}

function getQueueLabel(group) {
  if ((group.documents || []).some((document) => document.analysis_status === "failed")) return "Erreur pipeline";
  if (group.state === "non_compliant") return "Non conforme";
  if (group.state === "compliant") return "Conforme";
  if (group.status === "processing") return "Traitement en cours";
  if (group.status === "failed") return "Echec pipeline";
  return "En attente";
}

function getPipelineSummary(group) {
  if ((group.documents || []).some((document) => document.analysis_status === "failed")) {
    return "Un document a plante pendant le pipeline. Ouvrez son detail pour lire l'erreur technique retournee.";
  }

  if (group.status === "failed") {
    return "Le pipeline a echoue avant finalisation. Verifiez l'erreur technique retournee.";
  }

  if (group.status === "processing") {
    return "Le dossier attend encore la fin du pipeline OCR/extraction/validation.";
  }

  if (group.validation_result === "invalid" || group.state === "non_compliant") {
    return "Le traitement est termine avec des incoherences metier a revoir.";
  }

  if (group.validation_result === "valid" || group.state === "compliant") {
    return "Le traitement est termine et les champs consolides sont disponibles.";
  }

  return "Le dossier est encore en attente d'un retour complet du pipeline.";
}

function buildMetrics(groups) {
  const pending = groups.filter((group) => group.status === "processing" || group.validation_result === "pending").length;
  const flagged = groups.filter(
    (group) =>
      group.state === "non_compliant" ||
      group.validation_result === "invalid" ||
      (group.anomalies || []).length > 0 ||
      (group.fraud_flags || []).length > 0,
  ).length;
  const ready = groups.filter((group) => group.state === "compliant" || group.validation_result === "valid").length;

  return [
    { label: "Dossiers pending", value: String(pending).padStart(2, "0"), note: "Still moving through OCR or validation" },
    { label: "Flagged anomalies", value: String(flagged).padStart(2, "0"), note: "Require accountant attention" },
    { label: "Compliant dossiers", value: String(ready).padStart(2, "0"), note: "Ready for business follow-up" },
  ];
}

function buildDistribution(groups) {
  const compliant = groups.filter((group) => group.state === "compliant" || group.validation_result === "valid").length;
  const nonCompliant = groups.filter(
    (group) => group.state === "non_compliant" || group.validation_result === "invalid",
  ).length;
  const processing = groups.filter(
    (group) =>
      group.status === "processing" ||
      group.status === "pending" ||
      group.validation_result === "pending" ||
      group.state === "pending",
  ).length;
  const pipelineError = groups.filter((group) => (group.documents || []).some((document) => document.analysis_status === "failed")).length;

  return [
    { label: "Compliant", value: compliant, tone: "ok" },
    { label: "Non-compliant", value: nonCompliant, tone: "bad" },
    { label: "Processing", value: processing, tone: "warn" },
    { label: "Pipeline error", value: pipelineError, tone: "neutral" },
  ];
}

function buildFraudBreakdown(groups) {
  const counts = new Map();

  groups.forEach((group) => {
    (group.fraud_flags || []).forEach((flag) => {
      counts.set(flag, (counts.get(flag) || 0) + 1);
    });
  });

  return [...counts.entries()]
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => right.value - left.value)
    .slice(0, 5);
}

function buildRecentTimeline(groups) {
  return [...groups]
    .sort((left, right) => new Date(right.processed_at || right.updated_at || 0) - new Date(left.processed_at || left.updated_at || 0))
    .slice(0, 6)
    .map((group) => ({
      id: group.id,
      name: group.name,
      status: getQueueLabel(group),
      tone: getQueueTone(group),
      when: formatDate(group.processed_at || group.updated_at),
    }));
}

function getSummaryEntries(group) {
  const summary = group.extracted_summary || {};

  return [
    ["Supplier", summary.supplier_name],
    ["SIRET", summary.siret],
    ["IBAN", summary.iban],
    ["BIC", summary.bic],
    ["HT", summary.montant_ht],
    ["TTC", summary.montant_ttc],
    ["URSSAF", summary.urssaf_valid_until],
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");
}

function getPrimaryIssue(group) {
  const failedDocument = (group.documents || []).find((document) => document.analysis_status === "failed");
  if (failedDocument) {
    return `Erreur technique sur ${failedDocument.original_name || "un document"}.`;
  }

  return group.non_compliance_reason || group.anomalies?.[0] || group.error || "No blocking issue reported";
}

function getDocumentTypeLabel(documentType) {
  if (documentType === "invoice") return "Facture";
  if (documentType === "urssaf_certificate") return "Attestation URSSAF";
  if (documentType === "bank_details") return "RIB";
  return "Type en attente";
}

function getDocumentButtonLabel(document) {
  const typeLabel = getDocumentTypeLabel(document.document_type);
  if (document.document_type && document.document_type !== "unknown") {
    return typeLabel;
  }

  return document.original_name || "Document";
}

function DetailField({ label, value }) {
  return (
    <div className="detail-field">
      <span>{label}</span>
      <strong>{value || "Not available"}</strong>
    </div>
  );
}

function hasDisplayValue(value) {
  if (value === null || value === undefined) return false;
  if (typeof value === "string") return value.trim() !== "";
  if (Array.isArray(value)) return value.length > 0;
  return true;
}

function ModalShell({ title, onClose, children }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">CREATE</p>
            <h2>{title}</h2>
          </div>
          <button type="button" className="secondary-button modal-close" onClick={onClose}>
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function DistributionChart({ items }) {
  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <div className="chart-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">DOSSIER SPLIT</p>
          <h2>Status distribution</h2>
        </div>
        <span className="status-chip">{total} total</span>
      </div>
      <div className="distribution-chart">
        <div className="distribution-bars">
          {items.map((item) => {
            const width = total ? `${(item.value / total) * 100}%` : "0%";
            return (
              <div key={item.label} className="distribution-row">
                <div className="distribution-label">
                  <span className={`distribution-dot distribution-dot--${item.tone}`} />
                  <strong>{item.label}</strong>
                  <span>{item.value}</span>
                </div>
                <div className="distribution-track">
                  <div className={`distribution-fill distribution-fill--${item.tone}`} style={{ width }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function FraudChart({ items }) {
  const max = items[0]?.value || 0;

  return (
    <div className="chart-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">FRAUD SNAPSHOT</p>
          <h2>Most common flags</h2>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="dashboard-text">No fraud flag recorded yet.</p>
      ) : (
        <div className="fraud-chart">
          {items.map((item) => (
            <div key={item.label} className="fraud-row">
              <div className="fraud-row-head">
                <strong>{item.label}</strong>
                <span>{item.value}</span>
              </div>
              <div className="distribution-track">
                <div
                  className="distribution-fill distribution-fill--bad"
                  style={{ width: max ? `${(item.value / max) * 100}%` : "0%" }}
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TimelineChart({ items }) {
  return (
    <div className="chart-card">
      <div className="section-heading">
        <div>
          <p className="eyebrow">RECENT FLOW</p>
          <h2>Latest processed dossiers</h2>
        </div>
      </div>
      {items.length === 0 ? (
        <p className="dashboard-text">No processed dossier yet.</p>
      ) : (
        <div className="timeline-chart">
          {items.map((item) => (
            <div key={item.id} className="timeline-item">
              <span className={`timeline-dot timeline-dot--${item.tone}`} />
              <div className="timeline-body">
                <strong>{item.name}</strong>
                <p>{item.status}</p>
              </div>
              <span className="timeline-time">{item.when}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DocumentDetailModal({ detail, loading, onClose }) {
  if (!detail && !loading) return null;

  const extractedEntries = Object.entries(detail?.extracted_data || {}).filter(([, value]) => hasDisplayValue(value));
  const metaEntries = detail
    ? [
        ["Type", detail.document_type && detail.document_type !== "unknown" ? getDocumentTypeLabel(detail.document_type) : null],
        ["Analysis", detail.analysis_status],
        [
          "Confidence",
          detail.confidence_score !== null && detail.confidence_score !== undefined
            ? `${Math.round(detail.confidence_score * 100)}%`
            : null,
        ],
        ["Manual review", detail.needs_manual_review ? "Yes" : null],
        ["Pipeline step", detail.pipeline_step],
        ["Error", detail.error],
      ].filter(([, value]) => hasDisplayValue(value))
    : [];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel modal-panel--wide" onClick={(event) => event.stopPropagation()}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">DOCUMENT DETAIL</p>
            <h2>{loading ? "Loading document..." : detail.original_name}</h2>
          </div>
          <button type="button" className="secondary-button modal-close" onClick={onClose}>
            Close
          </button>
        </div>
        {loading ? (
          <p className="dashboard-text">Fetching OCR text and extracted fields...</p>
        ) : (
          <>
            {metaEntries.length ? (
              <div className="detail-grid">
                {metaEntries.map(([label, value]) => (
                  <DetailField key={label} label={label} value={value} />
                ))}
              </div>
            ) : null}

            {detail.anomalies?.length ? (
              <div className="detail-section">
                <p className="eyebrow">ANOMALIES</p>
                <ul className="inline-list">
                  {detail.anomalies.map((anomaly) => (
                    <li key={anomaly}>{anomaly}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {extractedEntries.length ? (
              <div className="detail-section">
                <p className="eyebrow">EXTRACTED DATA</p>
                <div className="detail-grid">
                  {extractedEntries.map(([key, value]) => (
                    <DetailField
                      key={key}
                      label={key}
                      value={Array.isArray(value) ? value.join(", ") : String(value)}
                    />
                  ))}
                </div>
              </div>
            ) : null}

            {detail.ocr_text ? (
              <div className="detail-section">
                <p className="eyebrow">OCR TEXT</p>
                <pre className="ocr-preview">{detail.ocr_text}</pre>
              </div>
            ) : null}
          </>
        )}
      </div>
    </div>
  );
}

export default function AccountantPage() {
  const accessToken = authStorage.getAccess();
  const [companies, setCompanies] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCompanyModal, setShowCompanyModal] = useState(false);
  const [showSupplierModal, setShowSupplierModal] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentLoading, setDocumentLoading] = useState(false);
  const [companyForm, setCompanyForm] = useState({
    name: "",
    registration_number: "",
    siret: "",
    vat_number: "",
    email: "",
  });
  const [supplierForm, setSupplierForm] = useState({
    name: "",
    registration_number: "",
    siret: "",
    vat_number: "",
    iban: "",
    bic: "",
    urssaf_expiration_date: "",
    email: "",
  });

  async function loadReviewData() {
    if (!accessToken) return;

    setLoading(true);

    try {
      const [companyData, supplierData, groupData] = await Promise.all([
        getCompanies(accessToken),
        getSuppliers(accessToken),
        getDocumentGroups(accessToken),
      ]);

      setCompanies(companyData);
      setSuppliers(supplierData);
      setGroups(groupData);
    } catch {
      toast.error("Unable to load accountant dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReviewData();
  }, []);

  async function handleCreateCompany(event) {
    event.preventDefault();

    try {
      await createCompany(accessToken, companyForm);
      toast.success("Company created");
      setCompanyForm({
        name: "",
        registration_number: "",
        siret: "",
        vat_number: "",
        email: "",
      });
      setShowCompanyModal(false);
      await loadReviewData();
    } catch {
      toast.error("Unable to create company");
    }
  }

  async function handleCreateSupplier(event) {
    event.preventDefault();

    try {
      await createSupplier(accessToken, supplierForm);
      toast.success("Supplier created");
      setSupplierForm({
        name: "",
        registration_number: "",
        siret: "",
        vat_number: "",
        iban: "",
        bic: "",
        urssaf_expiration_date: "",
        email: "",
      });
      setShowSupplierModal(false);
      await loadReviewData();
    } catch {
      toast.error("Unable to create supplier");
    }
  }

  async function handleOpenDocument(documentId) {
    setDocumentLoading(true);
    setSelectedDocument(null);

    try {
      const detail = await getDocumentDetail(accessToken, documentId);
      setSelectedDocument(detail);
    } catch {
      toast.error("Unable to load document detail");
    } finally {
      setDocumentLoading(false);
    }
  }

  const enrichedGroups = groups.map((group) => {
    const company = companies.find((item) => item.id === group.company_id);
    const supplier = suppliers.find((item) => item.id === group.supplier_id);

    return {
      ...group,
      companyName: company?.name || "Unlinked company",
      supplierName: supplier?.name || group.extracted_summary?.supplier_name || "Unlinked supplier",
      queueTone: getQueueTone(group),
      queueLabel: getQueueLabel(group),
      summaryEntries: getSummaryEntries(group),
      primaryIssue: getPrimaryIssue(group),
      updatedLabel: formatDate(group.processed_at || group.updated_at),
      createdByLabel: group.created_by_id || "Unknown submitter",
      pipelineSummary: getPipelineSummary(group),
    };
  });

  const reviewQueue = [...enrichedGroups].sort((left, right) => {
    const leftWeight = left.queueTone === "bad" ? 0 : left.queueTone === "warn" ? 1 : 2;
    const rightWeight = right.queueTone === "bad" ? 0 : right.queueTone === "warn" ? 1 : 2;
    return leftWeight - rightWeight;
  });

  const metrics = buildMetrics(enrichedGroups);
  const distribution = buildDistribution(enrichedGroups);
  const fraudBreakdown = buildFraudBreakdown(enrichedGroups);
  const recentTimeline = buildRecentTimeline(enrichedGroups);

  return (
    <main className="dashboard-page">
      <section className="dashboard-header">
        <div>
          <p className="eyebrow">ACCOUNTANT DASHBOARD</p>
          <h1>Read the dossier first, then drill into the document only when needed.</h1>
          <p className="dashboard-text">
            The backend already gives the main dashboard what it needs through `document_groups`: business state,
            pipeline status, fraud flags, anomalies, and extracted summary. Individual document detail is reserved for
            focused review.
          </p>
        </div>
        <div className="dashboard-actions">
          <button type="button" className="secondary-button" onClick={() => setShowCompanyModal(true)}>
            Add company
          </button>
          <button type="button" className="secondary-button" onClick={() => setShowSupplierModal(true)}>
            Add supplier
          </button>
          <button type="button" className="secondary-button" onClick={loadReviewData}>
            Refresh queue
          </button>
          <Link to="/" className="secondary-button">
            Main page
          </Link>
        </div>
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-card dashboard-card--highlight">
          <h2>Today&apos;s compliance totals</h2>
          <div className="metric-row">
            {metrics.map((metric) => (
              <div key={metric.label}>
                <span>{metric.label}</span>
                <strong>{metric.value}</strong>
                <p className="metric-note">{metric.note}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="dashboard-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">QUEUE FOCUS</p>
              <h2>Review priorities</h2>
            </div>
          </div>
          <ul className="check-list">
            <li>Use `state` for the business decision and `status` for technical progress.</li>
            <li>Read `fraud_flags` and top anomalies before opening any document detail.</li>
            <li>Trust `extracted_summary` for the quick synthesis across the dossier.</li>
            <li>Open a specific document only when OCR text or raw extracted fields matter.</li>
          </ul>
        </article>
      </section>

      <section className="dashboard-grid dashboard-grid--wide">
        <DistributionChart items={distribution} />
        <FraudChart items={fraudBreakdown} />
      </section>

      <section className="dashboard-grid">
        <TimelineChart items={recentTimeline} />
      </section>

      <section className="dashboard-grid dashboard-grid--wide">
        <article className="dashboard-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">SUPPLIER REVIEW QUEUE</p>
              <h2>All supplier dossiers</h2>
            </div>
            <span className="status-chip">Dashboard = document group synthesis</span>
          </div>

          {loading ? (
            <p className="dashboard-text">Loading review queue...</p>
          ) : reviewQueue.length === 0 ? (
            <p className="dashboard-text">No supplier dossier available yet.</p>
          ) : (
            <div className="dossier-list">
              {reviewQueue.map((group) => (
                <article key={group.id} className="dossier-card">
                  <div className="dossier-topline">
                    <strong>{group.name}</strong>
                    <span className={`status-pill status-pill--${group.queueTone}`}>{group.queueLabel}</span>
                  </div>
                  <p className="dossier-meta">{group.supplierName}</p>
                  <p className="dossier-meta">{group.companyName}</p>
                  <p className="dossier-progress">
                    Etat: {group.state || "pending"} • Pipeline: {group.status || "pending"} • Validation:{" "}
                    {group.validation_result || "pending"}
                  </p>
                  <p className="dossier-meta">{group.pipelineSummary}</p>
                  <p className="dossier-meta">Fraud flags: {(group.fraud_flags || []).join(", ") || "None"}</p>
                  <p className="dossier-meta">Processed at: {group.updatedLabel}</p>
                  <p className="dossier-meta">Submitted by: {group.createdByLabel}</p>
                  <p className="dossier-anomaly">{group.primaryIssue}</p>

                  {group.summaryEntries.length > 0 ? (
                    <div className="extract-chip-row">
                      {group.summaryEntries.map(([label, value]) => (
                        <span key={`${group.id}-${label}`} className="extract-chip">
                          {label}: {value}
                        </span>
                      ))}
                    </div>
                  ) : null}

                  {(group.anomalies || []).length > 1 ? (
                    <ul className="inline-list">
                      {group.anomalies.map((anomaly) => (
                        <li key={`${group.id}-${anomaly}`}>{anomaly}</li>
                      ))}
                    </ul>
                  ) : null}

                  {group.documents?.length ? (
                    <div className="document-action-row">
                      {group.documents.map((document) => (
                        <button
                          key={document.id}
                          type="button"
                          className="document-chip document-chip--neutral"
                          onClick={() => handleOpenDocument(document.id)}
                        >
                          Voir le detail • {getDocumentButtonLabel(document)}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </article>
              ))}
            </div>
          )}
        </article>

        <article className="dashboard-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">ACCOUNTANT NOTES</p>
              <h2>Latest anomaly feed</h2>
            </div>
          </div>

          {reviewQueue.length === 0 ? (
            <p className="dashboard-text">No active anomaly feed yet.</p>
          ) : (
            <ul className="activity-list">
              {reviewQueue.slice(0, 5).map((group) => (
                <li key={`${group.id}-feed`}>
                  <div>
                    <strong>{group.name}</strong>
                    <span>{group.primaryIssue}</span>
                  </div>
                  <span className={`status-pill status-pill--${group.queueTone}`}>{group.queueLabel}</span>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>

      {showCompanyModal ? (
        <ModalShell title="Add company" onClose={() => setShowCompanyModal(false)}>
          <form className="dashboard-form" onSubmit={handleCreateCompany}>
            <input
              className="custom-input"
              placeholder="Name"
              value={companyForm.name}
              onChange={(event) => setCompanyForm((current) => ({ ...current, name: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="Registration number"
              value={companyForm.registration_number}
              onChange={(event) => setCompanyForm((current) => ({ ...current, registration_number: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="SIRET"
              value={companyForm.siret}
              onChange={(event) => setCompanyForm((current) => ({ ...current, siret: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="VAT number"
              value={companyForm.vat_number}
              onChange={(event) => setCompanyForm((current) => ({ ...current, vat_number: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="Email"
              value={companyForm.email}
              onChange={(event) => setCompanyForm((current) => ({ ...current, email: event.target.value }))}
            />
            <button type="submit" className="custom-button">
              Create company
            </button>
          </form>
        </ModalShell>
      ) : null}

      {showSupplierModal ? (
        <ModalShell title="Add supplier" onClose={() => setShowSupplierModal(false)}>
          <form className="dashboard-form" onSubmit={handleCreateSupplier}>
            <input
              className="custom-input"
              placeholder="Name"
              value={supplierForm.name}
              onChange={(event) => setSupplierForm((current) => ({ ...current, name: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="Registration number"
              value={supplierForm.registration_number}
              onChange={(event) => setSupplierForm((current) => ({ ...current, registration_number: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="SIRET"
              value={supplierForm.siret}
              onChange={(event) => setSupplierForm((current) => ({ ...current, siret: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="VAT number"
              value={supplierForm.vat_number}
              onChange={(event) => setSupplierForm((current) => ({ ...current, vat_number: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="IBAN"
              value={supplierForm.iban}
              onChange={(event) => setSupplierForm((current) => ({ ...current, iban: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="BIC"
              value={supplierForm.bic}
              onChange={(event) => setSupplierForm((current) => ({ ...current, bic: event.target.value }))}
            />
            <input
              className="custom-input"
              type="date"
              value={supplierForm.urssaf_expiration_date}
              onChange={(event) => setSupplierForm((current) => ({ ...current, urssaf_expiration_date: event.target.value }))}
            />
            <input
              className="custom-input"
              placeholder="Email"
              value={supplierForm.email}
              onChange={(event) => setSupplierForm((current) => ({ ...current, email: event.target.value }))}
            />
            <button type="submit" className="custom-button">
              Create supplier
            </button>
          </form>
        </ModalShell>
      ) : null}

      <DocumentDetailModal
        detail={selectedDocument}
        loading={documentLoading}
        onClose={() => {
          setSelectedDocument(null);
          setDocumentLoading(false);
        }}
      />
    </main>
  );
}
