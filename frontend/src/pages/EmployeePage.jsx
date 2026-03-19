import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-hot-toast";

import { authStorage } from "../auth/authStorage";
import {
  createDocumentGroup,
  getDocumentDetail,
  getDocumentGroups,
  getSuppliers,
  uploadDocumentToGroup,
} from "../api/dashboardApi";

const uploadChecklist = [
  "Create one dossier per supplier submission.",
  "Attach the invoice, URSSAF certificate, and bank details.",
  "The supplier and company are extracted from the uploaded documents.",
  "If the dossier is compliant, the business entities can be created from extracted data later.",
];

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

function getStatusTone(group) {
  if ((group.documents || []).some((document) => document.analysis_status === "failed")) return "bad";
  if (group.state === "non_compliant" || group.validation_result === "invalid") return "bad";
  if (group.state === "compliant" || group.validation_result === "valid") return "ok";
  if (group.status === "processing" || group.validation_result === "pending") return "warn";
  return "neutral";
}

function getStatusLabel(group) {
  if ((group.documents || []).some((document) => document.analysis_status === "failed")) return "Erreur pipeline";
  if (group.state === "non_compliant") return "Non conforme";
  if (group.state === "compliant") return "Conforme";
  if (group.status === "processing") return "Traitement en cours";
  if (group.status === "failed") return "Echec pipeline";
  return "En attente";
}

function getPipelineSummary(group) {
  if ((group.documents || []).some((document) => document.analysis_status === "failed")) {
    return "Un document du dossier a echoue cote pipeline. Ouvrez le detail du document pour voir l'erreur technique.";
  }

  if (group.status === "failed") {
    return "Le pipeline a echoue. Ouvrez le dossier pour voir l'erreur retournee.";
  }

  if (group.status === "processing") {
    return "Les documents sont en cours d'OCR, de classification et de validation dans Airflow.";
  }

  if (group.validation_result === "invalid" || group.state === "non_compliant") {
    return "Le traitement est termine et le dossier contient des anomalies metier.";
  }

  if (group.validation_result === "valid" || group.state === "compliant") {
    return "Le traitement est termine et le dossier est exploitable cote metier.";
  }

  return "Le dossier a ete cree et attend encore un retour complet du pipeline.";
}

function getPrimaryIssue(group) {
  const failedDocument = (group.documents || []).find((document) => document.analysis_status === "failed");
  if (failedDocument) {
    return `Erreur technique sur ${failedDocument.original_name || "un document"}.`;
  }

  return group.anomalies?.[0] || group.error || "No blocking anomaly detected";
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

function buildSummaryChips(group) {
  const summary = group.extracted_summary || {};

  return [
    ["SIRET", summary.siret],
    ["IBAN", summary.iban],
    ["BIC", summary.bic],
    ["HT", summary.montant_ht],
    ["TTC", summary.montant_ttc],
    ["URSSAF", summary.urssaf_valid_until],
  ].filter(([, value]) => value !== undefined && value !== null && value !== "");
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

function DirectoryModal({ title, item, onClose, fields }) {
  if (!item) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel" onClick={(event) => event.stopPropagation()}>
        <div className="section-heading">
          <div>
            <p className="eyebrow">DETAILS</p>
            <h2>{title}</h2>
          </div>
          <button type="button" className="secondary-button modal-close" onClick={onClose}>
            Close
          </button>
        </div>
        <div className="detail-grid">
          {fields.map(([label, key]) => (
            <DetailField key={key} label={label} value={item[key]} />
          ))}
        </div>
      </div>
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
        ["Manual review", detail.needs_manual_review ? "Yes" : null],
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

export default function EmployeePage() {
  const accessToken = authStorage.getAccess();
  const [suppliers, setSuppliers] = useState([]);
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selectedSupplierCard, setSelectedSupplierCard] = useState(null);
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentLoading, setDocumentLoading] = useState(false);
  const [form, setForm] = useState({
    name: "",
    description: "",
  });
  const [files, setFiles] = useState([]);

  async function loadDashboardData() {
    if (!accessToken) return;

    setLoading(true);

    try {
      const [supplierData, groupData] = await Promise.all([
        getSuppliers(accessToken),
        getDocumentGroups(accessToken),
      ]);
      setSuppliers(supplierData);
      setGroups(groupData);
    } catch {
      toast.error("Unable to load employee dashboard");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDashboardData();
  }, []);

  function handleFileSelection(event) {
    const selectedFiles = Array.from(event.target.files || []);
    setFiles((current) => {
      const existingKeys = new Set(current.map((file) => `${file.name}-${file.size}-${file.lastModified}`));
      const nextFiles = selectedFiles.filter(
        (file) => !existingKeys.has(`${file.name}-${file.size}-${file.lastModified}`),
      );
      return [...current, ...nextFiles];
    });
    event.target.value = "";
  }

  function handleRemoveSelectedFile(fileToRemove) {
    setFiles((current) =>
      current.filter(
        (file) =>
          !(
            file.name === fileToRemove.name &&
            file.size === fileToRemove.size &&
            file.lastModified === fileToRemove.lastModified
          ),
      ),
    );
  }

  async function handleCreateDossier(event) {
    event.preventDefault();

    if (!form.name.trim()) {
      toast.error("Add a dossier name");
      return;
    }

    if (files.length === 0) {
      toast.error("Upload at least one document");
      return;
    }

    setSubmitting(true);

    try {
      const group = await createDocumentGroup(accessToken, {
        name: form.name.trim(),
        description: form.description.trim(),
      });

      await Promise.all(files.map((file) => uploadDocumentToGroup(accessToken, group.id, file)));

      toast.success("Dossier created and documents uploaded");
      setForm({
        name: "",
        description: "",
      });
      setFiles([]);
      await loadDashboardData();
    } catch {
      toast.error("Upload failed");
    } finally {
      setSubmitting(false);
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

  const dossiers = groups.map((group) => {
    const summary = group.extracted_summary || {};

    return {
      ...group,
      supplierName: summary.supplier_name || "Supplier extracted after validation",
      companyName: summary.company_name || "Company created from extracted data if compliant",
      statusLabel: getStatusLabel(group),
      statusTone: getStatusTone(group),
      summaryChips: buildSummaryChips(group),
      processedLabel: formatDate(group.processed_at),
      pipelineSummary: getPipelineSummary(group),
      primaryIssue: getPrimaryIssue(group),
    };
  });

  const recentSignals = groups
    .flatMap((group) =>
      (group.anomalies || []).slice(0, 2).map((anomaly) => ({
        id: `${group.id}-${anomaly}`,
        title: group.name,
        detail: anomaly,
      })),
    )
    .slice(0, 5);

  return (
    <main className="dashboard-page">
      <section className="dashboard-header">
        <div>
          <p className="eyebrow">EMPLOYEE DASHBOARD</p>
          <h1>Upload the dossier first. Business entities come from extraction.</h1>
          <p className="dashboard-text">
            Employees only create a document group and upload files. Supplier and company data are meant to be
            extracted from the documents, then created later if the dossier is compliant.
          </p>
        </div>
        <div className="dashboard-actions">
          <button type="button" className="secondary-button" onClick={loadDashboardData}>
            Refresh pipeline
          </button>
          <Link to="/" className="secondary-button">
            Main page
          </Link>
        </div>
      </section>

      <section className="dashboard-grid">
        <article className="dashboard-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">SUPPLIERS</p>
              <h2>Supplier directory</h2>
            </div>
          </div>
          <div className="compact-directory">
            <div className="compact-directory-block">
              <p className="eyebrow">KNOWN SUPPLIERS</p>
              <div className="compact-card-row">
                {suppliers.map((supplier) => (
                  <button
                    key={supplier.id}
                    type="button"
                    className="compact-card-button"
                    onClick={() => setSelectedSupplierCard(supplier)}
                  >
                    {supplier.name}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <ul className="check-list" style={{ marginTop: "1rem" }}>
            {uploadChecklist.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </article>

        <article className="dashboard-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">NEW DOSSIER</p>
              <h2>Create and upload</h2>
            </div>
          </div>
          <form className="dashboard-form" onSubmit={handleCreateDossier}>
            <input
              className="custom-input"
              placeholder="Dossier name"
              value={form.name}
              onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
            />
            <textarea
              className="dashboard-textarea"
              placeholder="Short description or notes"
              value={form.description}
              onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))}
            />
            <input
              className="dashboard-file-input"
              type="file"
              multiple
              accept=".pdf,.png,.jpg,.jpeg"
              onChange={handleFileSelection}
            />
            <p className="dashboard-text upload-help">
              Upload now, extraction later. This form no longer asks employees to choose companies or suppliers.
            </p>
            {files.length > 0 ? (
              <div className="selected-file-list">
                {files.map((file) => (
                  <div key={`${file.name}-${file.size}-${file.lastModified}`} className="selected-file-card">
                    <div>
                      <strong>{file.name}</strong>
                      <p className="dossier-meta">{Math.max(1, Math.round(file.size / 1024))} KB</p>
                    </div>
                    <button
                      type="button"
                      className="selected-file-remove"
                      onClick={() => handleRemoveSelectedFile(file)}
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
            <button type="submit" className="custom-button" disabled={submitting}>
              {submitting ? "Uploading..." : `Create dossier with ${files.length || 0} file${files.length === 1 ? "" : "s"}`}
            </button>
          </form>
        </article>
      </section>

      <section className="dashboard-grid dashboard-grid--wide">
        <article className="dashboard-card">
          <div className="section-heading">
            <div>
              <p className="eyebrow">SUPPLIER DOSSIERS</p>
              <h2>Document groups overview</h2>
            </div>
            <span className="status-chip">Main dashboard = group-level status first</span>
          </div>

          {loading ? (
            <p className="dashboard-text">Loading document groups...</p>
          ) : dossiers.length === 0 ? (
            <p className="dashboard-text">No supplier dossier yet. Create one above to start the validation flow.</p>
          ) : (
            <div className="dossier-list">
              {dossiers.map((group) => (
                <article key={group.id} className="dossier-card">
                  <div className="dossier-topline">
                    <strong>{group.name}</strong>
                    <span className={`status-pill status-pill--${group.statusTone}`}>{group.statusLabel}</span>
                  </div>
                  <p className="dossier-meta">{group.supplierName}</p>
                  <p className="dossier-meta">{group.companyName}</p>
                  <p className="dossier-meta">{group.pipelineSummary}</p>
                  <p className="dossier-meta">Processed at: {group.processedLabel}</p>
                  <p className="dossier-anomaly">{group.primaryIssue}</p>

                  {group.summaryChips.length > 0 ? (
                    <div className="extract-chip-row">
                      {group.summaryChips.map(([label, value]) => (
                        <span key={`${group.id}-${label}`} className="extract-chip">
                          {label}: {value}
                        </span>
                      ))}
                    </div>
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
              <p className="eyebrow">RECENT SIGNALS</p>
              <h2>Latest anomalies</h2>
            </div>
          </div>

          {recentSignals.length === 0 ? (
            <p className="dashboard-text">No anomaly returned yet. Refresh after the pipeline finishes processing.</p>
          ) : (
            <ul className="activity-list">
              {recentSignals.map((event) => (
                <li key={event.id}>
                  <div>
                    <strong>{event.title}</strong>
                    <span>{event.detail}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </article>
      </section>

      <DocumentDetailModal
        detail={selectedDocument}
        loading={documentLoading}
        onClose={() => {
          setSelectedDocument(null);
          setDocumentLoading(false);
        }}
      />
      <DirectoryModal
        title={selectedSupplierCard?.name}
        item={selectedSupplierCard}
        onClose={() => setSelectedSupplierCard(null)}
        fields={[
          ["Name", "name"],
          ["SIRET", "siret"],
          ["VAT", "vat_number"],
          ["IBAN", "iban"],
          ["BIC", "bic"],
          ["URSSAF expiry", "urssaf_expiration_date"],
        ]}
      />
    </main>
  );
}
