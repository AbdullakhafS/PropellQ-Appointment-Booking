import React, { useState, useEffect, useCallback, useRef } from 'react';
import { insuranceReviewApi } from '../../api/insuranceReviewApi';
import type {
  PendingInsuranceRow,
  PendingQuery,
  BatchVerifyRequest,
} from '../../types/insuranceReview';
import { VerificationSidePanel } from './VerificationSidePanel';
import styles from './InsuranceDashboard.module.css';

const STATUS_OPTIONS = ['unverified', 'manual_review', 'verified'] as const;
const DATE_RANGES = [
  { label: 'Next 7 days', value: 7 },
  { label: 'Next 14 days', value: 14 },
  { label: 'Next 30 days', value: 30 },
  { label: 'All dates', value: undefined },
] as const;

const STAFF_ID = 1; // Placeholder — real implementation reads from auth context

function ConfidenceBadge({ score }: { score: number }) {
  const cls = score >= 70 ? styles.badgeGreen : score >= 40 ? styles.badgeAmber : styles.badgeRed;
  return <span className={`${styles.badge} ${cls}`}>{score}%</span>;
}

function StatusBadge({ status }: { status: string }) {
  const cls =
    status === 'verified' ? styles.statusVerified :
    status === 'unverified' ? styles.statusUnverified :
    styles.statusManual;
  return <span className={`${styles.statusBadge} ${cls}`}>{status.replace('_', ' ')}</span>;
}

export function InsuranceDashboard() {
  const [rows, setRows] = useState<PendingInsuranceRow[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState<PendingQuery>({
    status: 'unverified',
    sortBy: 'date',
    sortAsc: true,
    page: 1,
    pageSize: 50,
  });

  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [activePanelId, setActivePanelId] = useState<number | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = (msg: string) => {
    setToast(msg);
    if (toastTimer.current) clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 3500);
  };

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await insuranceReviewApi.getPending(query);
      setRows(result.items);
      setTotalCount(result.totalCount);
    } catch {
      setError('Failed to load verifications. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [query]);

  useEffect(() => { load(); }, [load]);

  const toggleSelect = (id: number) =>
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleSelectAll = () =>
    setSelectedIds(prev =>
      prev.size === rows.length ? new Set() : new Set(rows.map(r => r.id))
    );

  const handleBatchVerify = async () => {
    if (selectedIds.size === 0) return;
    const req: BatchVerifyRequest = {
      ids: [...selectedIds],
      staffId: STAFF_ID,
      newStatus: 'verified',
      verificationMethod: 'portal',
    };
    try {
      const result = await insuranceReviewApi.verifyBatch(req);
      showToast(`${result.updated.length} record(s) verified.${result.failedCount > 0 ? ` ${result.failedCount} failed.` : ''}`);
      setSelectedIds(new Set());
      await load();
    } catch {
      showToast('Batch verify failed. Please try again.');
    }
  };

  const handleExportCsv = () => {
    const header = ['ID', 'Patient Name', 'Insurance Name', 'Member ID', 'Confidence', 'Status', 'Created At'];
    const csvRows = rows.map(r => [
      r.id, r.patientName ?? '', r.insuranceName ?? '', r.memberId ?? '',
      r.confidenceScore, r.verificationStatus,
      new Date(r.createdAt).toLocaleString(),
    ].join(','));
    const blob = new Blob([header.join(',') + '\n' + csvRows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `insurance-verifications-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleVerifySuccess = async () => {
    showToast('Verification updated.');
    setActivePanelId(null);
    await load();
  };

  const activeRow = activePanelId !== null ? rows.find(r => r.id === activePanelId) ?? null : null;

  return (
    <div className={styles.page}>
      <header className={styles.pageHeader}>
        <h1 className={styles.title}>Pending Insurance Verifications</h1>
        <p className={styles.subtitle}>
          {loading ? 'Loading…' : `${totalCount} record(s) found`}
        </p>
      </header>

      {/* Filters */}
      <div className={styles.filters} role="search" aria-label="Filter verifications">
        <div className={styles.filterGroup}>
          <label htmlFor="filter-status" className={styles.filterLabel}>Status</label>
          <select
            id="filter-status"
            className={styles.select}
            value={query.status ?? ''}
            onChange={e => setQuery(q => ({ ...q, status: e.target.value || undefined, page: 1 }))}
          >
            <option value="">All</option>
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
          </select>
        </div>
        <div className={styles.filterGroup}>
          <label htmlFor="filter-date" className={styles.filterLabel}>Date range</label>
          <select
            id="filter-date"
            className={styles.select}
            value={query.dateRangeDays ?? ''}
            onChange={e => setQuery(q => ({ ...q, dateRangeDays: e.target.value ? Number(e.target.value) : undefined, page: 1 }))}
          >
            {DATE_RANGES.map(d => <option key={d.label} value={d.value ?? ''}>{d.label}</option>)}
          </select>
        </div>
        <div className={styles.filterGroup}>
          <label htmlFor="filter-ins" className={styles.filterLabel}>Insurance</label>
          <input
            id="filter-ins"
            className={styles.input}
            placeholder="Plan name…"
            value={query.insurance ?? ''}
            onChange={e => setQuery(q => ({ ...q, insurance: e.target.value || undefined, page: 1 }))}
          />
        </div>
        <button type="button" className={styles.refreshBtn} onClick={load} aria-label="Refresh">
          Refresh
        </button>
      </div>

      {/* Toolbar */}
      <div className={styles.toolbar}>
        <label className={styles.selectAllLabel}>
          <input
            type="checkbox"
            checked={selectedIds.size === rows.length && rows.length > 0}
            onChange={toggleSelectAll}
            aria-label="Select all rows"
          />
          {selectedIds.size > 0 ? `${selectedIds.size} selected` : 'Select all'}
        </label>
        <button
          type="button"
          className={styles.batchBtn}
          onClick={handleBatchVerify}
          disabled={selectedIds.size === 0}
          aria-disabled={selectedIds.size === 0}
        >
          ✓ Mark Selected as Verified
        </button>
        <button type="button" className={styles.exportBtn} onClick={handleExportCsv}>
          Export CSV
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div className={styles.errorBanner} role="alert">
          {error}
          <button type="button" onClick={load} className={styles.retryBtn}>Retry</button>
        </div>
      )}

      {/* Loading skeleton / table */}
      {loading && rows.length === 0 ? (
        <div className={styles.skeletonWrapper} aria-busy="true" aria-label="Loading…">
          {[...Array(5)].map((_, i) => <div key={i} className={styles.skeletonRow} />)}
        </div>
      ) : rows.length === 0 ? (
        <div className={styles.emptyState} role="status">
          <p className={styles.emptyIcon} aria-hidden="true">🎉</p>
          <p className={styles.emptyTitle}>All insurances verified!</p>
          <p className={styles.emptySubtitle}>Great job keeping data clean.</p>
        </div>
      ) : (
        <div className={styles.tableWrapper}>
          <table className={styles.table} aria-label="Insurance verification records">
            <thead>
              <tr>
                <th className={styles.th} aria-label="Select row" />
                <th className={styles.th}>Patient</th>
                <th className={styles.th}>Insurance</th>
                <th className={styles.th}>Member ID</th>
                <th
                  className={`${styles.th} ${styles.sortable}`}
                  onClick={() => setQuery(q => ({ ...q, sortBy: 'confidence', sortAsc: !q.sortAsc }))}
                  aria-sort={query.sortBy === 'confidence' ? (query.sortAsc ? 'ascending' : 'descending') : 'none'}
                  tabIndex={0}
                  role="columnheader"
                >
                  Confidence {query.sortBy === 'confidence' ? (query.sortAsc ? '↑' : '↓') : ''}
                </th>
                <th className={styles.th}>Status</th>
                <th
                  className={`${styles.th} ${styles.sortable}`}
                  onClick={() => setQuery(q => ({ ...q, sortBy: 'date', sortAsc: !q.sortAsc }))}
                  aria-sort={query.sortBy === 'date' ? (query.sortAsc ? 'ascending' : 'descending') : 'none'}
                  tabIndex={0}
                  role="columnheader"
                >
                  Created {query.sortBy === 'date' ? (query.sortAsc ? '↑' : '↓') : ''}
                </th>
                <th className={styles.th}>Action</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr
                  key={row.id}
                  className={`${styles.tr} ${row.verificationStatus === 'unverified' ? styles.trUnverified : row.verificationStatus === 'verified' ? styles.trVerified : styles.trManual}`}
                >
                  <td className={styles.td}>
                    <input
                      type="checkbox"
                      checked={selectedIds.has(row.id)}
                      onChange={() => toggleSelect(row.id)}
                      aria-label={`Select record ${row.id}`}
                    />
                  </td>
                  <td className={styles.td}>
                    <button
                      type="button"
                      className={styles.patientLink}
                      onClick={() => setActivePanelId(row.id)}
                      aria-label={`Open details for ${row.patientName ?? `Patient ${row.patientId}`}`}
                    >
                      {row.patientName ?? `Patient #${row.patientId}`}
                    </button>
                  </td>
                  <td className={styles.td}>{row.insuranceName ?? '—'}</td>
                  <td className={styles.td}><code>{row.memberId ?? '—'}</code></td>
                  <td className={styles.td}><ConfidenceBadge score={row.confidenceScore} /></td>
                  <td className={styles.td}><StatusBadge status={row.verificationStatus} /></td>
                  <td className={styles.td}>
                    {new Date(row.createdAt).toLocaleDateString()}
                  </td>
                  <td className={styles.td}>
                    <button
                      type="button"
                      className={styles.reviewBtn}
                      onClick={() => setActivePanelId(row.id)}
                    >
                      Review
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalCount > (query.pageSize ?? 50) && (
        <div className={styles.pagination}>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={(query.page ?? 1) <= 1}
            onClick={() => setQuery(q => ({ ...q, page: Math.max(1, (q.page ?? 1) - 1) }))}
          >
            ← Previous
          </button>
          <span>Page {query.page ?? 1} of {Math.ceil(totalCount / (query.pageSize ?? 50))}</span>
          <button
            type="button"
            className={styles.pageBtn}
            disabled={(query.page ?? 1) >= Math.ceil(totalCount / (query.pageSize ?? 50))}
            onClick={() => setQuery(q => ({ ...q, page: (q.page ?? 1) + 1 }))}
          >
            Next →
          </button>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className={styles.toast} role="status" aria-live="polite">{toast}</div>
      )}

      {/* Side panel */}
      {activeRow && (
        <VerificationSidePanel
          row={activeRow}
          staffId={STAFF_ID}
          onClose={() => setActivePanelId(null)}
          onVerifySuccess={handleVerifySuccess}
        />
      )}
    </div>
  );
}
