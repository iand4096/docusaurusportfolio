import {createContext} from 'react';

export const DiagramFigureContext = createContext(false);
export type DiagramDirection = 'TB' | 'LR';

export const DiagramDirectionContext = createContext<DiagramDirection | undefined | null>(null);
