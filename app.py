import os

files = {
    "package.json": '''{
  "name": "client-details-wizard",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.4.1"
  }
}
''',

    "vite.config.js": '''import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
});
''',

    "index.html": '''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Mortgage Loan Wizard — Client Details</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
''',

    "src/main.jsx": '''import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
''',

    "src/App.jsx": '''import React from "react";
import ClientDetails from "./components/ClientDetails";

export default function App() {
  function handleContinue(data) {
    console.log("Validated borrower data:", data);
    window.alert("Client Details validated. Proceeding to Mortgage step (not yet implemented).");
  }

  return <ClientDetails onContinue={handleContinue} />;
}
''',

    "src/utils/validation.js": '''// Validation helpers for the Client Details form

export const emailRegex = /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/;
export const phoneRegex = /^\\(?\\d{3}\\)?[-.\\s]?\\d{3}[-.\\s]?\\d{4}$/;

export function validateBorrower(borrower) {
  const errors = {};

  if (!borrower.fullName || !borrower.fullName.trim()) {
    errors.fullName = "Full name is required.";
  }

  if (!borrower.dateOfBirth) {
    errors.dateOfBirth = "Date of birth is required.";
  } else {
    const dob = new Date(borrower.dateOfBirth);
    const today = new Date();
    if (Number.isNaN(dob.getTime())) {
      errors.dateOfBirth = "Enter a valid date.";
    } else if (dob > today) {
      errors.dateOfBirth = "Date of birth cannot be in the future.";
    }
  }

  if (!borrower.gender) {
    errors.gender = "Please select an option.";
  }

  if (!borrower.maritalStatus) {
    errors.maritalStatus = "Please select an option.";
  }

  if (!borrower.phone || !borrower.phone.trim()) {
    errors.phone = "Phone number is required.";
  } else if (!phoneRegex.test(borrower.phone.trim())) {
    errors.phone = "Enter a valid 10-digit phone number.";
  }

  if (!borrower.email || !borrower.email.trim()) {
    errors.email = "Email is required.";
  } else if (!emailRegex.test(borrower.email.trim())) {
    errors.email = "Enter a valid email address.";
  }

  if (!borrower.address || !borrower.address.trim()) {
    errors.address = "Current address is required.";
  }

  return errors;
}

export function validateAllBorrowers(borrowers) {
  const errorsList = borrowers.map(validateBorrower);
  const isValid = errorsList.every((e) => Object.keys(e).length === 0);
  return { errorsList, isValid };
}

export function formatPhoneInput(value) {
  const digits = value.replace(/\\D/g, "").slice(0, 10);
  if (digits.length <= 3) return digits;
  if (digits.length <= 6) return `(${digits.slice(0, 3)}) ${digits.slice(3)}`;
  return `(${digits.slice(0, 3)}) ${digits.slice(3, 6)}-${digits.slice(6)}`;
}

export function createEmptyBorrower() {
  return {
    fullName: "",
    dateOfBirth: "",
    gender: "",
    maritalStatus: "",
    phone: "",
    email: "",
    address: "",
  };
}
''',

    "src/components/ClientDetails.jsx": '''import React, { useState } from "react";
import {
  validateAllBorrowers,
  formatPhoneInput,
  createEmptyBorrower,
} from "../utils/validation";
import "./ClientDetails.css";

const STEPS = ["Client Details", "Mortgage", "Income", "Debts", "Analysis"];

export default function ClientDetails({ onContinue, onBack }) {
  const [borrowerCount, setBorrowerCount] = useState(1);
  const [borrowers, setBorrowers] = useState([createEmptyBorrower()]);
  const [errors, setErrors] = useState([{}]);
  const [consentChecked, setConsentChecked] = useState(false);
  const [consentError, setConsentError] = useState("");
  const [showRefreshDialog, setShowRefreshDialog] = useState(false);
  const [expanded, setExpanded] = useState({ 0: true });

  function handleBorrowerCountChange(count) {
    setBorrowerCount(count);
    setBorrowers((prev) => {
      const next = [...prev];
      if (count > prev.length) {
        for (let i = prev.length; i < count; i++) {
          next.push(createEmptyBorrower());
        }
      } else {
        next.length = count;
      }
      return next;
    });
    setErrors((prev) => {
      const next = [...prev];
      next.length = count;
      for (let i = 0; i < count; i++) {
        if (!next[i]) next[i] = {};
      }
      return next;
    });
    setExpanded((prev) => {
      const next = { ...prev };
      for (let i = 0; i < count; i++) {
        if (next[i] === undefined) next[i] = true;
      }
      return next;
    });
  }

  function updateField(index, field, value) {
    setBorrowers((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
    setErrors((prev) => {
      const next = [...prev];
      if (next[index] && next[index][field]) {
        const updated = { ...next[index] };
        delete updated[field];
        next[index] = updated;
      }
      return next;
    });
  }

  function toggleExpanded(index) {
    setExpanded((prev) => ({ ...prev, [index]: !prev[index] }));
  }

  function handleRefreshClick() {
    setShowRefreshDialog(true);
  }

  function confirmRefresh() {
    setBorrowerCount(1);
    setBorrowers([createEmptyBorrower()]);
    setErrors([{}]);
    setConsentChecked(false);
    setConsentError("");
    setExpanded({ 0: true });
    setShowRefreshDialog(false);
  }

  function cancelRefresh() {
    setShowRefreshDialog(false);
  }

  function handleContinue() {
    const { errorsList, isValid } = validateAllBorrowers(borrowers);
    setErrors(errorsList);

    let consentOk = true;
    if (!consentChecked) {
      setConsentError("You must acknowledge and consent before continuing.");
      consentOk = false;
    } else {
      setConsentError("");
    }

    if (isValid && consentOk) {
      onContinue && onContinue({ borrowers });
    } else {
      const toExpand = {};
      errorsList.forEach((e, i) => {
        if (Object.keys(e).length > 0) toExpand[i] = true;
      });
      setExpanded((prev) => ({ ...prev, ...toExpand }));
    }
  }

  return (
    <div className="cd-page">
      <header className="cd-header">
        <div className="cd-header-icon" aria-hidden="true">
          <HomeIcon />
        </div>
        <div>
          <h1 className="cd-header-title">FH Mortgage Loan Wizard</h1>
          <p className="cd-header-subtitle">Residential Mortgage Application</p>
        </div>
      </header>

      <div className="cd-card">
        <ol className="cd-stepper" aria-label="Application progress">
          {STEPS.map((label, i) => (
            <li
              key={label}
              className={`cd-step ${i === 0 ? "cd-step-active" : ""}`}
            >
              <span className="cd-step-circle">{i + 1}</span>
              <span className="cd-step-label">{label}</span>
              {i < STEPS.length - 1 && <span className="cd-step-line" />}
            </li>
          ))}
        </ol>

        <h2 className="cd-section-title">Client Details</h2>
        <p className="cd-section-subtitle">
          Enter information for each borrower on this application.
        </p>

        <fieldset className="cd-borrower-count">
          <legend>Number of Borrowers</legend>
          <div className="cd-count-options">
            {[1, 2, 3, 4].map((n) => (
              <button
                type="button"
                key={n}
                className={`cd-count-btn ${
                  borrowerCount === n ? "cd-count-btn-active" : ""
                }`}
                onClick={() => handleBorrowerCountChange(n)}
                aria-pressed={borrowerCount === n}
              >
                {n}
              </button>
            ))}
          </div>
        </fieldset>

        {borrowers.map((borrower, index) => (
          <BorrowerSection
            key={index}
            index={index}
            borrower={borrower}
            errors={errors[index] || {}}
            expanded={!!expanded[index]}
            onToggle={() => toggleExpanded(index)}
            onChange={(field, value) => updateField(index, field, value)}
          />
        ))}

        <div className="cd-consent">
          <h3 className="cd-consent-title">Consent</h3>
          <p className="cd-consent-text">
            By proceeding, you acknowledge and consent to the collection,
            use, and disclosure of your personal information for the purpose
            of processing this application. Your information will be kept
            confidential and used solely for this purpose. You have the
            right to access and correct your personal information at any
            time.
          </p>
          <label className="cd-checkbox-row">
            <input
              type="checkbox"
              checked={consentChecked}
              onChange={(e) => {
                setConsentChecked(e.target.checked);
                if (e.target.checked) setConsentError("");
              }}
            />
            <span>I acknowledge and consent to the above terms</span>
          </label>
          {consentError && <p className="cd-error">{consentError}</p>}
        </div>

        <div className="cd-nav-buttons">
          <button type="button" className="cd-btn cd-btn-secondary" onClick={() => (onBack ? onBack() : window.alert("This is the first screen."))}>
            ← Back
          </button>
          <button type="button" className="cd-btn cd-btn-secondary" onClick={handleRefreshClick}>
            Refresh
          </button>
          <button type="button" className="cd-btn cd-btn-primary" onClick={handleContinue}>
            Continue →
          </button>
        </div>
      </div>

      {showRefreshDialog && (
        <div className="cd-modal-overlay" role="dialog" aria-modal="true">
          <div className="cd-modal">
            <p>
              Are you sure you want to refresh? All entered data will be
              permanently cleared.
            </p>
            <div className="cd-modal-buttons">
              <button type="button" className="cd-btn cd-btn-secondary" onClick={cancelRefresh}>
                Cancel
              </button>
              <button type="button" className="cd-btn cd-btn-danger" onClick={confirmRefresh}>
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function BorrowerSection({ index, borrower, errors, expanded, onToggle, onChange }) {
  return (
    <div className="cd-borrower-card">
      <button type="button" className="cd-borrower-header" onClick={onToggle}>
        <span className="cd-borrower-header-left">
          <span className="cd-borrower-icon" aria-hidden="true">
            <PersonIcon />
          </span>
          <span className="cd-borrower-title">Borrower {index + 1}</span>
        </span>
        <span className={`cd-chevron ${expanded ? "cd-chevron-up" : ""}`}>▾</span>
      </button>

      {expanded && (
        <div className="cd-borrower-body">
          <div className="cd-field-row">
            <Field label="Full Name" error={errors.fullName}>
              <input
                type="text"
                placeholder="Jane Smith"
                value={borrower.fullName}
                onChange={(e) => onChange("fullName", e.target.value)}
              />
            </Field>
            <Field label="Email Address" error={errors.email}>
              <input
                type="email"
                placeholder="jane@example.com"
                value={borrower.email}
                onChange={(e) => onChange("email", e.target.value)}
              />
            </Field>
          </div>

          <div className="cd-field-row">
            <Field label="Phone Number" error={errors.phone}>
              <input
                type="tel"
                placeholder="(416) 555-0100"
                value={borrower.phone}
                onChange={(e) => onChange("phone", formatPhoneInput(e.target.value))}
              />
            </Field>
            <Field label="Date of Birth" error={errors.dateOfBirth}>
              <input
                type="date"
                value={borrower.dateOfBirth}
                onChange={(e) => onChange("dateOfBirth", e.target.value)}
              />
            </Field>
          </div>

          <div className="cd-field-row">
            <Field label="Gender" error={errors.gender}>
              <select
                value={borrower.gender}
                onChange={(e) => onChange("gender", e.target.value)}
              >
                <option value="">Select...</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
                <option value="prefer_not_to_say">Prefer not to say</option>
              </select>
            </Field>
            <Field label="Marital Status" error={errors.maritalStatus}>
              <select
                value={borrower.maritalStatus}
                onChange={(e) => onChange("maritalStatus", e.target.value)}
              >
                <option value="">Select...</option>
                <option value="single">Single</option>
                <option value="married">Married</option>
                <option value="divorced">Divorced</option>
                <option value="widowed">Widowed</option>
                <option value="common_law">Common-Law</option>
              </select>
            </Field>
          </div>

          <div className="cd-field-row cd-field-row-single">
            <Field label="Current Address" error={errors.address}>
              <textarea
                rows={2}
                placeholder="123 Main St, Toronto, ON M5V 1A1"
                value={borrower.address}
                onChange={(e) => onChange("address", e.target.value)}
              />
            </Field>
          </div>
        </div>
      )}
    </div>
  );
}

function Field({ label, error, children }) {
  return (
    <div className="cd-field">
      <label className="cd-field-label">{label}</label>
      {children}
      {error && <p className="cd-error">{error}</p>}
    </div>
  );
}

function HomeIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
      <path d="M3 11.5L12 4l9 7.5" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5 10v9a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1v-9" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function PersonIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="8" r="4" stroke="#2563EB" strokeWidth="2" />
      <path d="M4 20c0-4.4 3.6-7 8-7s8 2.6 8 7" stroke="#2563EB" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}
''',

    "src/components/ClientDetails.css": '''/* Client Details — mortgage wizard step 1 */

.cd-page {
  min-height: 100vh;
  background: #f3f4f6;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  padding: 24px 16px 64px;
  color: #1f2933;
}

.cd-header {
  max-width: 900px;
  margin: 0 auto 24px;
  display: flex;
  align-items: center;
  gap: 14px;
}

.cd-header-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  background: #2563eb;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cd-header-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
}

.cd-header-subtitle {
  margin: 2px 0 0;
  font-size: 14px;
  color: #6b7280;
}

.cd-card {
  max-width: 900px;
  margin: 0 auto;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.cd-stepper {
  display: flex;
  list-style: none;
  padding: 0;
  margin: 0 0 32px;
}

.cd-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  text-align: center;
}

.cd-step-circle {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #e5e7eb;
  color: #6b7280;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  z-index: 1;
}

.cd-step-active .cd-step-circle {
  background: #2563eb;
  color: #fff;
}

.cd-step-label {
  margin-top: 8px;
  font-size: 13px;
  color: #9ca3af;
}

.cd-step-active .cd-step-label {
  color: #111827;
  font-weight: 600;
}

.cd-step-line {
  position: absolute;
  top: 17px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: #e5e7eb;
  z-index: 0;
}

.cd-section-title {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 6px;
}

.cd-section-subtitle {
  font-size: 14px;
  color: #6b7280;
  margin: 0 0 24px;
}

.cd-borrower-count {
  border: none;
  padding: 0;
  margin: 0 0 28px;
}

.cd-borrower-count legend {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 10px;
  padding: 0;
}

.cd-count-options {
  display: flex;
  gap: 10px;
}

.cd-count-btn {
  width: 48px;
  height: 44px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
  background: #fff;
  font-size: 15px;
  font-weight: 600;
  color: #374151;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}

.cd-count-btn:hover {
  border-color: #93c5fd;
}

.cd-count-btn-active {
  background: #2563eb;
  border-color: #2563eb;
  color: #fff;
}

.cd-borrower-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 20px;
  overflow: hidden;
}

.cd-borrower-header {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f9fafb;
  border: none;
  padding: 16px 18px;
  cursor: pointer;
  font-size: 15px;
}

.cd-borrower-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.cd-borrower-icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #dbeafe;
  display: flex;
  align-items: center;
  justify-content: center;
}

.cd-borrower-title {
  font-weight: 600;
  color: #111827;
}

.cd-chevron {
  color: #9ca3af;
  transition: transform 0.15s;
}

.cd-chevron-up {
  transform: rotate(180deg);
}

.cd-borrower-body {
  padding: 20px 18px 6px;
}

.cd-field-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 16px;
}

.cd-field-row-single {
  grid-template-columns: 1fr;
}

.cd-field {
  display: flex;
  flex-direction: column;
}

.cd-field-label {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  margin-bottom: 6px;
}

.cd-field input,
.cd-field select,
.cd-field textarea {
  border: 1px solid #d1d5db;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: 14px;
  font-family: inherit;
  color: #111827;
  background: #fff;
  resize: vertical;
}

.cd-field input:focus,
.cd-field select:focus,
.cd-field textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.cd-error {
  margin: 6px 0 0;
  font-size: 12.5px;
  color: #dc2626;
}

.cd-consent {
  border-top: 1px solid #e5e7eb;
  padding-top: 24px;
  margin-top: 8px;
}

.cd-consent-title {
  font-size: 15px;
  font-weight: 700;
  margin: 0 0 8px;
}

.cd-consent-text {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0 0 14px;
}

.cd-checkbox-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 14px;
  cursor: pointer;
}

.cd-checkbox-row input {
  margin-top: 3px;
}

.cd-nav-buttons {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 28px;
}

.cd-btn {
  padding: 11px 22px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: background 0.15s, opacity 0.15s;
}

.cd-btn-secondary {
  background: #fff;
  border: 1px solid #d1d5db;
  color: #374151;
}

.cd-btn-secondary:hover {
  background: #f9fafb;
}

.cd-btn-primary {
  background: #2563eb;
  color: #fff;
  margin-left: auto;
}

.cd-btn-primary:hover {
  background: #1d4ed8;
}

.cd-btn-danger {
  background: #dc2626;
  color: #fff;
}

.cd-btn-danger:hover {
  background: #b91c1c;
}

.cd-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 50;
}

.cd-modal {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  max-width: 380px;
  width: 100%;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
}

.cd-modal p {
  margin: 0 0 20px;
  font-size: 14px;
  color: #374151;
  line-height: 1.5;
}

.cd-modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 640px) {
  .cd-card {
    padding: 20px;
  }
  .cd-field-row {
    grid-template-columns: 1fr;
  }
  .cd-step-label {
    font-size: 11px;
  }
  .cd-nav-buttons {
    flex-wrap: wrap;
  }
  .cd-btn-primary {
    margin-left: 0;
    width: 100%;
    order: 3;
  }
}
''',
}

for path, content in files.items():
    full_path = os.path.join(os.getcwd(), path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True) if os.path.dirname(path) else None
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Created", len(files), "files.")
