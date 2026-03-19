import { Link, useNavigate } from "react-router-dom";
import { toast } from "react-hot-toast";
import { authStorage } from "../auth/authStorage";

const featureCards = [
  {
    title: "Supplier Dossiers",
    description: "Group each supplier submission into one dossier with the invoice, URSSAF certificate, and RIB.",
  },
  {
    title: "Validation Signals",
    description: "Surface missing documents, anomalies, and compliance issues before the accounting handoff.",
  },
  {
    title: "Accounting Handoff",
    description: "Send cleaner supplier files to review with clearer status, extracted fields, and business context.",
  },
];

export default function MainPage() {
  const navigate = useNavigate();
  const access = authStorage.getAccess();
  const role = authStorage.getRole();
  const dashboardPath = role === "Accountant" ? "/dashboard/accountant" : "/dashboard/employee";
  const isLoggedIn = Boolean(access && role);

  function handleLogout() {
    authStorage.clear();
    toast.success("Logged out successfully");
    navigate("/");
  }

  return (
    <main className="landing-page">
      <section className="landing-hero">
        <div className="landing-copy">
          <p className="eyebrow">DOC AI WORKSPACE</p>
          <h1>Move from document drop-off to finance action in one flow.</h1>
          <p className="landing-text">
            Turn raw supplier uploads into structured dossiers, prepare invoice, URSSAF, and bank documents for
            validation, and move cleaner cases into accounting review.
          </p>
          <div className="landing-actions">
            {isLoggedIn ? (
              <>
                <Link to={dashboardPath} className="custom-button">
                  Go to dashboard
                </Link>
                <button type="button" className="secondary-button" onClick={handleLogout}>
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link to="/login" className="custom-button">
                  Login
                </Link>
                <Link to="/register" className="secondary-button">
                  Create account
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      <section className="feature-grid" aria-label="Platform highlights">
        {featureCards.map((card) => (
          <article key={card.title} className="feature-card">
            <h3>{card.title}</h3>
            <p>{card.description}</p>
          </article>
        ))}
      </section>
    </main>
  );
}
