import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';

/**
 * Application shell.
 *
 * Navigation is labelled, never icon-led. These users read, and an icon rail
 * would cost a second of guessing on every hop through a forty-package review.
 *
 * The rail is grouped by what an inspector is doing rather than by data model:
 * the review loop first because it is the job, then lookup, then the registries
 * that make the system's own workings inspectable.
 */

const GROUPS: { heading: string; items: { to: string; label: string }[] }[] = [
  {
    heading: 'Build',
    items: [{ to: '/dashboard', label: 'New WPQR' }],
  },
  {
    heading: 'Review',
    items: [{ to: '/packages', label: 'Package worklist' }],
  },
  {
    heading: 'Lookup',
    items: [
      { to: '/welders', label: 'Welder registry' },
      { to: '/continuity', label: 'Continuity' },
      { to: '/joint-lookup', label: 'Joint lookup' },
    ],
  },
  {
    heading: 'Reference',
    items: [
      { to: '/rules', label: 'Rule tables' },
      { to: '/templates', label: 'Form templates' },
      { to: '/settings', label: 'Settings' },
    ],
  },
];

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden">
      <nav className="no-print flex w-[188px] shrink-0 flex-col border-r border-rule bg-paper">
        <div className="border-b border-rule px-4 py-3">
          <div className="font-cond text-lg font-semibold leading-none tracking-tight text-ink">
            Complyx
          </div>
          <div className="titleblock mt-1">ASME Sec. IX</div>
        </div>

        <div className="flex-1 overflow-y-auto py-3">
          {GROUPS.map((group) => (
            <div key={group.heading} className="mb-4">
              <div className="label px-4 pb-1">{group.heading}</div>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/dashboard'}
                  className={({ isActive }) =>
                    `block border-l-2 px-4 py-1.5 font-sans text-sm transition-colors duration-120 ${
                      isActive
                        ? 'border-blueprint bg-blueprint-soft font-medium text-blueprint'
                        : 'border-transparent text-graphite hover:bg-white hover:text-ink'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </div>

        {/*
          Deployment mode is shown, not hidden in settings. On an air-gapped
          site an inspector needs to know nothing left the building.
        */}
        <div className="border-t border-rule px-4 py-2">
          <div className="label">Deployment</div>
          <div className="font-mono text-2xs text-graphite">on-premise</div>
        </div>
      </nav>

      <main className="flex min-w-0 flex-1 flex-col overflow-hidden">{children}</main>
    </div>
  );
}
