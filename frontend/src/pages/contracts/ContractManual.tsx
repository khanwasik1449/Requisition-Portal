import { PageStyle } from '@/components/PageStyle'

// contracts/templates/contracts/manual.html -- <style> block, verbatim.
const css = `
  .manual {
    max-width: 800px;
    margin: 0 auto;
    font-size: 14px;
    line-height: 1.7;
    color: #1A1917;
  }
  .manual h2 {
    font-size: 22px;
    margin: 32px 0 12px;
    padding-bottom: 8px;
    border-bottom: 2px solid #2563EB;
    color: #0F172A;
  }
  .manual h3 {
    font-size: 17px;
    margin: 24px 0 8px;
    color: #1E293B;
  }
  .manual h4 {
    font-size: 14px;
    margin: 16px 0 6px;
    color: #334155;
  }
  .manual p, .manual li {
    color: #475569;
  }
  .manual ul, .manual ol {
    padding-left: 22px;
    margin-bottom: 12px;
  }
  .manual li {
    margin-bottom: 4px;
  }
  .manual .note {
    background: #FFF7ED;
    border-left: 4px solid #F97316;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 12px 0;
    font-size: 13px;
  }
  .manual .tip {
    background: #EFF6FF;
    border-left: 4px solid #2563EB;
    padding: 12px 16px;
    border-radius: 8px;
    margin: 12px 0;
    font-size: 13px;
  }
  .manual code {
    background: #F1F5F9;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 13px;
  }
  .manual kbd {
    background: #1E293B;
    color: #fff;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 12px;
  }
  .manual a {
    color: #2563EB;
  }
  .manual .toc {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 24px;
  }
  .manual .toc ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }
  .manual .toc li {
    padding: 4px 0;
  }
  .manual .toc a {
    text-decoration: none;
  }
  .manual .toc a:hover {
    text-decoration: underline;
  }
  .manual table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 13px;
  }
  .manual th, .manual td {
    border: 1px solid #E2E8F0;
    padding: 8px 12px;
    text-align: left;
  }
  .manual th {
    background: #F8FAFC;
    font-weight: 600;
  }
  .manual   hr {
    border: none;
    border-top: 1px solid #E2E8F0;
    margin: 28px 0;
  }
  @media print {
    .sidebar, .topbar, .sidebar-footer, .logout-btn, .mobile-toggle {
      display: none !important;
    }
    .main {
      margin-left: 0 !important;
      padding: 0 !important;
    }
    .content-card {
      border: none !important;
      box-shadow: none !important;
      padding: 0 !important;
    }
    .manual {
      font-size: 12px;
    }
    .manual h2 {
      page-break-after: avoid;
    }
    .manual h3 {
      page-break-after: avoid;
    }
    button {
      display: none !important;
    }
  }
`

// Replica of contracts/templates/contracts/manual.html
export function ContractManual() {
  return (
    <>
      <PageStyle css={css} />

      <div className="manual">
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <h1 style={{ fontSize: '28px', marginBottom: '4px' }}>
            📖 HR Contract System Manual
          </h1>
          <p style={{ color: '#64748B', fontSize: '14px' }}>
            Version 1.0 — BRAC Institute of Educational Development, BRAC University
          </p>
          <button
            type="button"
            onClick={() => window.print()}
            style={{
              marginTop: '12px',
              padding: '8px 20px',
              background: '#2563EB',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              fontSize: '13px',
              cursor: 'pointer',
            }}
          >
            🖨️ Download / Print
          </button>
        </div>

        {/* ─── Table of Contents ─── */}
        <div className="toc">
          <strong style={{ fontSize: '15px' }}>Table of Contents</strong>
          <ul>
            <li>
              <a href="#overview">1. System Overview</a>
            </li>
            <li>
              <a href="#login">2. Login / Logout</a>
            </li>
            <li>
              <a href="#dashboard">3. Dashboard</a>
            </li>
            <li>
              <a href="#contracts">4. Contract Management</a>
              <ul>
                <li>
                  <a href="#create">4.1 Creating a Contract</a>
                </li>
                <li>
                  <a href="#list">4.2 Contract List & Filtering</a>
                </li>
                <li>
                  <a href="#bulk-upload">4.3 Bulk Upload (CSV)</a>
                </li>
                <li>
                  <a href="#pdf">4.4 Generating PDF</a>
                </li>
                <li>
                  <a href="#email">4.5 Sending Contract via Email</a>
                </li>
                <li>
                  <a href="#bulk-email">4.6 Bulk Email</a>
                </li>
                <li>
                  <a href="#delete">4.7 Deleting a Contract</a>
                </li>
              </ul>
            </li>
            <li>
              <a href="#payslips">5. Payslip Management</a>
            </li>
            <li>
              <a href="#employees">6. Employee Management</a>
            </li>
            <li>
              <a href="#filters">7. Date Range & Status Filters</a>
            </li>
            <li>
              <a href="#sidebar">8. Sidebar Navigation</a>
            </li>
            <li>
              <a href="#tech">9. Technical Information</a>
            </li>
          </ul>
        </div>

        {/* ─── 1. Overview ─── */}
        <h2 id="overview">1. System Overview</h2>
        <p>
          The HR Contract System is a web-based application for managing employee contracts at BRAC
          Institute of Educational Development (BRAC IED), BRAC University. It allows HR staff to:
        </p>
        <ul>
          <li>Create, view, and manage contracts for employees</li>
          <li>Generate PDF versions of contracts (New, Extension, Revision, Renewal)</li>
          <li>Send contracts via email to employees individually or in bulk</li>
          <li>Upload contracts in bulk using CSV files</li>
          <li>Create and manage payslips</li>
          <li>Manage employee records</li>
          <li>Filter contracts by date range, status, and contract type</li>
        </ul>

        {/* ─── 2. Login / Logout ─── */}
        <h2 id="login">2. Login / Logout</h2>
        <p>
          The system is accessible at the server's IP address (e.g.,{' '}
          <code>http://115.127.4.12:8000</code>).
        </p>
        <ul>
          <li>
            <strong>Login:</strong> Enter your username and password on the login page. Check{' '}
            <em>Remember me</em> to stay logged in longer.
          </li>
          <li>
            <strong>Logout:</strong> Click the <strong>Logout</strong> button in the sidebar footer.
          </li>
        </ul>
        <div className="tip">
          If you are redirected to the login page, your session may have expired. Simply log in
          again.
        </div>

        {/* ─── 3. Dashboard ─── */}
        <h2 id="dashboard">3. Dashboard</h2>
        <p>
          After logging in, you land on the Dashboard. It shows a summary of all contracts in the
          system. The sidebar menu on the left provides access to all features.
        </p>

        {/* ─── 4. Contract Management ─── */}
        <h2 id="contracts">4. Contract Management</h2>

        <h3 id="create">4.1 Creating a Contract</h3>
        <ol>
          <li>
            Click <strong>Create Contract</strong> in the sidebar.
          </li>
          <li>
            Fill in the form:
            <ul>
              <li>
                <strong>PIN</strong> — Employee's unique PIN (required)
              </li>
              <li>
                <strong>Name</strong> — Employee's full name
              </li>
              <li>
                <strong>Designation</strong> — Job title
              </li>
              <li>
                <strong>Salary</strong> — Monthly salary in BDT
              </li>
              <li>
                <strong>Start Date / End Date</strong> — Contract period (required)
              </li>
              <li>
                <strong>Contract Type</strong> — New / Extension / Revision / Renewal
              </li>
              <li>
                <strong>New Designation</strong> — Only for Renewal contracts (optional)
              </li>
            </ul>
          </li>
          <li>
            Click <strong>Submit</strong>. A success popup appears with options to send the contract
            via email.
          </li>
        </ol>

        <h3 id="list">4.2 Contract List & Filtering</h3>
        <p>
          Click <strong>Contracts List</strong> in the sidebar. This page shows all contracts in a
          table with the following features:
        </p>
        <ul>
          <li>
            <strong>Status badges</strong> — Active (blue), Expired (red), Upcoming (yellow)
          </li>
          <li>
            <strong>Stat cards</strong> — Click Total, Active, Expired, Upcoming to filter
          </li>
          <li>
            <strong>Contract type filter</strong> — Filter by New, Extension, Revision, Renewal
          </li>
          <li>
            <strong>Date range filter</strong> — Filter by Start Date or End Date range
          </li>
          <li>
            <strong>Search</strong> — Search by name, PIN, or designation
          </li>
          <li>
            <strong>Checkboxes</strong> — Select multiple contracts for bulk email
          </li>
          <li>
            <strong>Bulk Email button</strong> — Sends email to all selected contracts
          </li>
        </ul>

        <h3 id="bulk-upload">4.3 Bulk Upload (CSV)</h3>
        <ol>
          <li>
            Click <strong>Bulk Contracts</strong> in the sidebar.
          </li>
          <li>
            Prepare a CSV file with the following columns:
            <br />
            <code>PIN, Name, Designation, Salary, Start Date, End Date, Contract Type</code>
            <br />
            Optional: <code>Email, Phone, TIN, New Designation</code>
          </li>
          <li>
            Click <strong>⬇ Download CSV</strong> to get a template with sample data.
          </li>
          <li>
            Upload the CSV file and click <strong>Upload CSV</strong>.
          </li>
        </ol>
        <div className="note">
          If a PIN already exists in the system, the employee's information will be updated with the
          CSV data.
        </div>

        <h3 id="pdf">4.4 Generating PDF</h3>
        <p>
          From the Contract List, click the <strong>📄</strong> (PDF) icon on any contract row. The
          PDF is generated automatically and downloaded. Each contract type uses a different
          template:
        </p>
        <ul>
          <li>
            <strong>New</strong> — Appointment letter format
          </li>
          <li>
            <strong>Extension</strong> — Extension of contract letter
          </li>
          <li>
            <strong>Revision</strong> — Revision of contract letter
          </li>
          <li>
            <strong>Renewal</strong> — Renewal of contract letter
          </li>
        </ul>

        <h3 id="email">4.5 Sending Contract via Email</h3>
        <p>
          From the Contract List, click the <strong>📧</strong> (Email) icon. The email form opens
          with auto-filled subject and body. You can edit the message before sending. The contract
          PDF is attached automatically.
        </p>

        <h3 id="bulk-email">4.6 Bulk Email</h3>
        <ol>
          <li>On the Contract List page, check the boxes for contracts you want to email.</li>
          <li>
            Click the <strong>📧 Bulk Email</strong> button.
          </li>
          <li>Enter the subject and body for the email.</li>
          <li>
            Click <strong>Send</strong>. The system processes emails in the background.
          </li>
          <li>
            You are redirected to a <strong>progress page</strong> showing sent/pending/failed
            counts.
          </li>
          <li>The page auto-refreshes until all emails are sent.</li>
        </ol>
        <div className="tip">
          Bulk email runs in the background — you can continue using the system while emails are
          being sent.
        </div>

        <h3 id="delete">4.7 Deleting a Contract</h3>
        <p>
          Click the <strong>🗑️</strong> (Delete) icon on any contract row and confirm the deletion.
        </p>

        {/* ─── 5. Payslip ─── */}
        <h2 id="payslips">5. Payslip Management</h2>
        <ul>
          <li>
            <strong>Create Payslip</strong> — Enter employee PIN, month, year, and salary details to
            generate a payslip.
          </li>
          <li>
            <strong>Payslip List</strong> — View, search, and download payslips as PDF.
          </li>
        </ul>

        {/* ─── 6. Employees ─── */}
        <h2 id="employees">6. Employee Management</h2>
        <ul>
          <li>
            <strong>Employee List</strong> — View all employees with their details.
          </li>
          <li>
            <strong>Add Employee</strong> — Add a new employee to the system.
          </li>
          <li>
            <strong>Import</strong> — Bulk import employees from CSV.
          </li>
        </ul>

        {/* ─── 7. Filters ─── */}
        <h2 id="filters">7. Date Range & Status Filters</h2>
        <p>The Contract List page supports multiple filtering options:</p>
        <ul>
          <li>
            <strong>Status:</strong> Click stat cards (Total / Active / Expired / Upcoming)
          </li>
          <li>
            <strong>Type:</strong> Select from the Contract Type dropdown
          </li>
          <li>
            <strong>Date Range:</strong> Use the Start Date and End Date fields to filter by
            contract period
          </li>
          <li>
            <strong>Search:</strong> Type in the search box to filter by name, PIN, or designation
          </li>
        </ul>

        {/* ─── 8. Sidebar ─── */}
        <h2 id="sidebar">8. Sidebar Navigation</h2>
        <p>The sidebar on the left provides navigation to all sections:</p>
        <table>
          <tbody>
            <tr>
              <th>Menu Item</th>
              <th>Description</th>
            </tr>
            <tr>
              <td>Create Contract</td>
              <td>Create a new contract</td>
            </tr>
            <tr>
              <td>Bulk Contracts</td>
              <td>Upload contracts via CSV</td>
            </tr>
            <tr>
              <td>Contracts List</td>
              <td>View, filter, email, and manage contracts</td>
            </tr>
            <tr>
              <td>Create Payslip</td>
              <td>Generate a new payslip</td>
            </tr>
            <tr>
              <td>Payslip List</td>
              <td>View and download payslips</td>
            </tr>
            <tr>
              <td>Employees</td>
              <td>Manage employee records</td>
            </tr>
            <tr>
              <td>Manual</td>
              <td>This documentation</td>
            </tr>
          </tbody>
        </table>

        {/* ─── 9. Technical ─── */}
        <h2 id="tech">9. Technical Information</h2>
        <ul>
          <li>
            <strong>Server:</strong> Gunicorn (WSGI) with 2 workers
          </li>
          <li>
            <strong>Background Tasks:</strong> Django Q2 for async email processing
          </li>
          <li>
            <strong>PDF Generation:</strong> WeasyPrint
          </li>
          <li>
            <strong>Database:</strong> SQLite
          </li>
          <li>
            <strong>Email:</strong> SMTP via Gmail (bracu.ied@bracu.ac.bd)
          </li>
          <li>
            <strong>Static Files:</strong> WhiteNoise for production serving
          </li>
          <li>
            <strong>Reset:</strong> System auto-starts on server reboot (systemd services)
          </li>
        </ul>

        <hr />

        <div
          style={{
            textAlign: 'center',
            padding: '16px',
            color: '#94A3B8',
            fontSize: '13px',
          }}
        >
          © 2026 BRAC Institute of Educational Development, BRAC University. All rights reserved.
        </div>
      </div>
    </>
  )
}
