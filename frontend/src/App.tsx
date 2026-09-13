import { Navigate, Route, Routes } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { Worklist } from '@/screens/Worklist';
import { PackageDetail } from '@/screens/PackageDetail';
import { CheckboxReview } from '@/screens/CheckboxReview';
import { Stub } from '@/screens/Stub';
import { WpqrFlow } from '@/screens/wpqr/WpqrFlow';

/**
 * Routes.
 *
 * The home route is the WPQR build flow: upload three source documents, check
 * they agree, derive the qualified range under Section IX, sign it off. That is
 * the job.
 *
 * The package review loop (worklist -> package detail -> reconciliation) moved
 * to /packages. It is a real screen set but it serves a product that needs
 * persistence and a queue of stored packages, neither of which exists — so it
 * is no longer the front door.
 *
 * The rest are stubs that state what belongs there and what blocks them, rather
 * than mocks that would suggest more exists than does.
 */
export default function App() {
  return (
    <AppShell>
      <Routes>
        {/* The product: three sources in, one signed WPQR out. */}
        <Route path="/" element={<WpqrFlow />} />
        <Route path="/packages" element={<Worklist />} />
        <Route path="/package/:id" element={<PackageDetail />} />
        <Route path="/package/:id/checkbox/:checkboxId" element={<CheckboxReview />} />
        <Route path="/checkbox-review" element={<CheckboxReview />} />

        <Route
          path="/intake"
          element={
            <Stub
              eyebrow="Review"
              title="New package intake"
              designRef="DESIGN.md §6, screen 4"
              blockedBy="Package assembler (build step 3) and the upload API (step 8). Classification already works, so the recognised-format readout is real once an endpoint exists."
              contents={[
                'Multi-file drop zone — a package arrives as a batch, not one document at a time',
                'Per-file classification readout: format number, revision, document type, confidence',
                'The six slots filling as files are assigned, so completeness is visible before processing starts',
                'An unclassified tray marked TEMPLATE UNKNOWN — never a silent guess into a slot',
              ]}
            />
          }
        />
        <Route
          path="/welders"
          element={
            <Stub
              eyebrow="Lookup"
              title="Welder registry"
              designRef="DESIGN.md §6, screen 13"
              blockedBy="Persistence (build step 7). Qualified ranges must be stored before they can be listed."
              contents={[
                'Every welder on the project: name, ID, processes and positions qualified',
                'Last qualification date and continuity status',
                'Photograph where the identity card carries one — stored, never exported',
              ]}
            />
          }
        />
        <Route
          path="/continuity"
          element={
            <Stub
              eyebrow="Lookup"
              title="Continuity"
              designRef="DESIGN.md §6, screen 15"
              clause="QW-322"
              blockedBy="Persistence (build step 7). The arithmetic is trivial; the stored qualification dates are not there yet."
              contents={[
                'A timeline, not a table: weeks across, welders down, qualification windows as bars',
                'The six-month lapse point marked on each bar',
                'Bars entering the next 30 days turn ochre',
                'Answers "these 14 welders lapse in 30 days" — which nobody tracks properly today',
              ]}
            />
          }
        />
        <Route
          path="/joint-lookup"
          element={
            <Stub
              eyebrow="Lookup"
              title="Joint-to-welder lookup"
              designRef="DESIGN.md §6, screen 16"
              blockedBy="Derivation engine (step 6) and persistence (step 7). Needs stored qualified ranges to query against."
              contents={[
                'Input: process, position, base metal P-number, thickness, pipe or plate, diameter',
                'Output: welders qualified for that joint, as a ruled list',
                'Fast, no ceremony — this is used standing next to a weld',
                'The screen that makes the tool live on site rather than in the QA office',
              ]}
            />
          }
        />
        <Route
          path="/rules"
          element={
            <Stub
              eyebrow="Reference"
              title="Rule tables"
              designRef="DESIGN.md §6, screen 17"
              blockedBy="Section IX rule tables (build step 5) are not yet encoded."
              contents={[
                'The QW tables as encoded: QW-423, QW-433, QW-451/452, QW-461.9, QW-402.4, QW-405.3',
                'Each entry showing its clause reference, its values, and its verification state',
                'Unverified entries carrying a visible ochre mark',
                'A reviewer can mark an entry verified, recording who and when',
                'This screen makes the product’s honesty legible — an auditor asking "where did this number come from" gets an answer',
              ]}
            />
          }
        />
        <Route
          path="/templates"
          element={
            <Stub
              eyebrow="Reference"
              title="Form templates"
              designRef="DESIGN.md §6, screen 18"
              blockedBy="Read-only view is buildable now against the registry; editing needs the template authoring API."
              contents={[
                'The known forms: TF-127-R0 and FQ-069-R2 are built; TF-114, TF-053, TF-216 and the lab report are not',
                'Format number, revision, document type, and the field region map',
                'Verification state per template — both shipped templates are currently unverified',
                'Where a new template gets defined when an unknown form appears',
              ]}
            />
          }
        />
        <Route
          path="/settings"
          element={
            <Stub
              eyebrow="Reference"
              title="Settings"
              designRef="DESIGN.md §6, screen 19"
              blockedBy="Auth and org scoping (build step 7)."
              contents={[
                'Project and team',
                'Retention policy — uploaded documents are deleted after extraction; only structured values are kept',
                'Deployment mode: hosted or on-premise',
              ]}
            />
          }
        />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AppShell>
  );
}
