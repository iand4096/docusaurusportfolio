export type DiagramRole = 'input' | 'process' | 'storage' | 'infra' | 'decision' | 'interaction' | 'generation';
export const roles: Readonly<Record<DiagramRole, Readonly<{
  label: string;
  fill: string;
  stroke: string;
  icon: string | null;
}>>>;
export function prepareMermaid(source: string): string;
export function flowchartWithDirection(source: string, direction: 'TB' | 'LR'): string | null;
export function flowchartDirection(source: string): 'TB' | 'LR' | undefined;
export const groupStyles: Readonly<Record<DiagramRole, Readonly<{fill: string; stroke: string}>>>;
