// FILE: ui/frontend/src/components/ArtifactTree.tsx
// File tree browser for run artifacts

import { useEffect, useState } from 'react';
import type { Artifact, FileContent } from '../types';
import { listArtifacts, getArtifactFile } from '../api/client';

interface Props {
    runId: string;
}

interface TreeNode {
    name: string;
    path: string;
    type: 'file' | 'directory';
    size?: number;
    children: TreeNode[];
}

export function ArtifactTree({ runId }: Props) {
    const [artifacts, setArtifacts] = useState<Artifact[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedFile, setSelectedFile] = useState<string | null>(null);
    const [fileContent, setFileContent] = useState<FileContent | null>(null);
    const [fileLoading, setFileLoading] = useState(false);
    const [expandedDirs, setExpandedDirs] = useState<Set<string>>(new Set());

    useEffect(() => {
        loadArtifacts();
    }, [runId]);

    async function loadArtifacts() {
        setLoading(true);
        try {
            const data = await listArtifacts(runId);
            setArtifacts(data.artifacts);
        } catch (err) {
            console.error('Failed to load artifacts:', err);
        } finally {
            setLoading(false);
        }
    }

    async function loadFile(path: string) {
        setSelectedFile(path);
        setFileLoading(true);
        try {
            const content = await getArtifactFile(runId, path);
            setFileContent(content);
        } catch (err) {
            console.error('Failed to load file:', err);
            setFileContent(null);
        } finally {
            setFileLoading(false);
        }
    }

    function toggleDir(path: string) {
        setExpandedDirs((prev) => {
            const next = new Set(prev);
            if (next.has(path)) {
                next.delete(path);
            } else {
                next.add(path);
            }
            return next;
        });
    }

    function buildTree(artifacts: Artifact[]): TreeNode[] {
        const root: TreeNode[] = [];
        const map = new Map<string, TreeNode>();

        // Sort so directories come first
        const sorted = [...artifacts].sort((a, b) => {
            if (a.type !== b.type) {
                return a.type === 'directory' ? -1 : 1;
            }
            return a.path.localeCompare(b.path);
        });

        for (const artifact of sorted) {
            const parts = artifact.path.split('/');
            const name = parts[parts.length - 1];

            const node: TreeNode = {
                name,
                path: artifact.path,
                type: artifact.type,
                size: artifact.size,
                children: [],
            };

            if (parts.length === 1) {
                root.push(node);
            } else {
                const parentPath = parts.slice(0, -1).join('/');
                const parent = map.get(parentPath);
                if (parent) {
                    parent.children.push(node);
                }
            }

            if (artifact.type === 'directory') {
                map.set(artifact.path, node);
            }
        }

        return root;
    }

    function formatSize(bytes?: number): string {
        if (bytes === undefined) return '';
        if (bytes < 1024) return `${bytes} B`;
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function getFileIcon(name: string): string {
        if (name.endsWith('.json') || name.endsWith('.jsonl')) return '📄';
        if (name.endsWith('.log')) return '📋';
        if (name.endsWith('.py')) return '🐍';
        if (name.endsWith('.diff') || name.endsWith('.patch')) return '🔀';
        if (name.endsWith('.md')) return '📝';
        return '📄';
    }

    function renderNode(node: TreeNode, depth = 0): JSX.Element {
        const isExpanded = expandedDirs.has(node.path);
        const isSelected = selectedFile === node.path;

        if (node.type === 'directory') {
            return (
                <div key={node.path}>
                    <button
                        onClick={() => toggleDir(node.path)}
                        className={`w-full flex items-center gap-2 px-2 py-1 hover:bg-gray-100 rounded text-left text-sm`}
                        style={{ paddingLeft: `${depth * 16 + 8}px` }}
                    >
                        <span className="text-gray-500">{isExpanded ? '📂' : '📁'}</span>
                        <span className="text-gray-700">{node.name}</span>
                    </button>
                    {isExpanded && (
                        <div>
                            {node.children.map((child) => renderNode(child, depth + 1))}
                        </div>
                    )}
                </div>
            );
        }

        return (
            <button
                key={node.path}
                onClick={() => loadFile(node.path)}
                className={`w-full flex items-center justify-between gap-2 px-2 py-1 hover:bg-gray-100 rounded text-left text-sm ${isSelected ? 'bg-primary-50 text-primary-700' : ''
                    }`}
                style={{ paddingLeft: `${depth * 16 + 8}px` }}
            >
                <div className="flex items-center gap-2 truncate">
                    <span>{getFileIcon(node.name)}</span>
                    <span className="truncate">{node.name}</span>
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap">
                    {formatSize(node.size)}
                </span>
            </button>
        );
    }

    const tree = buildTree(artifacts);

    if (loading) {
        return (
            <div className="p-8 text-center text-gray-500">Loading artifacts...</div>
        );
    }

    return (
        <div className="h-full flex">
            {/* File tree */}
            <div className="w-64 border-r bg-white overflow-y-auto">
                <div className="p-2 border-b bg-gray-50">
                    <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-gray-700">Files</span>
                        <button
                            onClick={loadArtifacts}
                            className="text-xs text-gray-500 hover:text-gray-700"
                        >
                            Refresh
                        </button>
                    </div>
                </div>
                <div className="p-1">{tree.map((node) => renderNode(node))}</div>
            </div>

            {/* File content */}
            <div className="flex-1 flex flex-col overflow-hidden">
                {selectedFile ? (
                    <>
                        <div className="p-2 border-b bg-gray-50 flex items-center justify-between">
                            <span className="text-sm text-gray-700 truncate">
                                {selectedFile}
                            </span>
                            {fileContent?.truncated && (
                                <span className="text-xs text-orange-600">
                                    Truncated ({formatSize(fileContent.total_size)})
                                </span>
                            )}
                        </div>
                        <div className="flex-1 overflow-auto">
                            {fileLoading ? (
                                <div className="p-4 text-gray-500">Loading...</div>
                            ) : fileContent?.content ? (
                                <pre className="p-4 text-sm font-mono whitespace-pre-wrap">
                                    {fileContent.content}
                                </pre>
                            ) : (
                                <div className="p-4 text-gray-500">Unable to display file</div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex items-center justify-center text-gray-400">
                        Select a file to view
                    </div>
                )}
            </div>
        </div>
    );
}
