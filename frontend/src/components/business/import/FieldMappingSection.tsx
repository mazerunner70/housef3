import React from 'react';
import { FieldMap } from '@/services/FileMapService';
import './FieldMappingSection.css';

interface FieldMappingSectionProps {
    mapping?: FieldMap | null;
    hasFiles: boolean;
    isLoading?: boolean;
    error?: string | null;
    onCreateMapping: () => void;
    onEditMapping: (mapping: FieldMap) => void;
    onDeleteMapping: (mappingId: string) => void;
    onViewMapping: (mapping: FieldMap) => void;
}

/**
 * FieldMappingSection - Streamlined field mapping interface
 * 
 * Adapted from ImportStep2Preview with focus on:
 * - Current mapping status display
 * - Quick actions for mapping management
 * - Clear status indicators
 * - Simplified interface for account context
 * 
 * Features:
 * - Display current field mapping configuration
 * - Create/edit/delete mapping actions
 * - Status indicators for mapping completeness
 * - Integration with existing field mapping system
 * - Responsive design with clear call-to-actions
 */
const FieldMappingSection: React.FC<FieldMappingSectionProps> = ({
    mapping,
    hasFiles,
    isLoading = false,
    error = null,
    onCreateMapping,
    onEditMapping,
    onDeleteMapping,
    onViewMapping
}) => {
    // Format mapping fields for display
    const formatMappingFields = (fieldMap: FieldMap): string[] => {
        if (!fieldMap.mappings || fieldMap.mappings.length === 0) {
            return ['No fields mapped'];
        }

        return fieldMap.mappings.map(mapping =>
            `${mapping.targetField}: ${mapping.sourceField}`
        );
    };

    // Get mapping status
    const getMappingStatus = () => {
        if (!hasFiles) {
            return {
                type: 'info' as const,
                icon: 'ℹ️',
                title: 'Field Mapping',
                message: 'Upload at least one transaction file to configure field mappings.'
            };
        }

        if (!mapping) {
            return {
                type: 'warning' as const,
                icon: '⚠️',
                title: 'Field Mapping Required',
                message: 'Transaction files have been uploaded but no field mapping has been configured. A field mapping tells the system which columns contain transaction data.'
            };
        }

        return {
            type: 'success' as const,
            icon: '✅',
            title: 'Field Mapping Configured',
            message: `Using "${mapping.name}" field mapping configuration.`
        };
    };

    const status = getMappingStatus();

    // Loading state
    if (isLoading) {
        return (
            <div className="field-mapping-section">
                <h3 className="mapping-section-title">Field Mapping</h3>
                <div className="mapping-loading">
                    <div className="loading-spinner"></div>
                    <p>Loading field mapping...</p>
                </div>
            </div>
        );
    }

    // Error state
    if (error) {
        return (
            <div className="field-mapping-section">
                <h3 className="mapping-section-title">Field Mapping</h3>
                <div className="mapping-error">
                    <span className="error-icon">⚠️</span>
                    <p>{error}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="field-mapping-section">
            <h3 className="mapping-section-title">Field Mapping</h3>

            <div className={`mapping-status ${status.type}`}>
                <div className="status-content">
                    <div className="status-header">
                        <span className="status-icon" role="img" aria-label={status.title}>
                            {status.icon}
                        </span>
                        <h4 className="status-title">{status.title}</h4>
                    </div>
                    <p className="status-message">{status.message}</p>

                    {/* Current Mapping Details */}
                    {mapping && (
                        <div className="current-mapping-details">
                            <div className="mapping-info">
                                <div className="mapping-name">
                                    <strong>{mapping.name}</strong>
                                    {mapping.description && (
                                        <span className="mapping-description"> - {mapping.description}</span>
                                    )}
                                </div>
                                <div className="mapping-fields">
                                    {formatMappingFields(mapping).map((field, index) => (
                                        <div key={index} className="mapped-field">
                                            <span className="field-icon">✓</span>
                                            <span className="field-text">{field}</span>
                                        </div>
                                    ))}
                                </div>
                                {mapping.reverseAmounts && (
                                    <div className="mapping-option">
                                        <span className="option-icon">🔄</span>
                                        <span className="option-text">Amount reversal enabled</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                {/* Action Buttons */}
                <div className="mapping-actions">
                    {!mapping && hasFiles && (
                        <button
                            onClick={onCreateMapping}
                            className="action-button action-primary"
                        >
                            <span className="action-icon">➕</span>
                            <span className="action-text">Create Field Mapping</span>
                        </button>
                    )}

                    {mapping && (
                        <>
                            <button
                                onClick={() => onViewMapping(mapping)}
                                className="action-button action-secondary"
                                title="View mapping details"
                            >
                                <span className="action-icon">👁️</span>
                                <span className="action-text">View</span>
                            </button>

                            <button
                                onClick={() => onEditMapping(mapping)}
                                className="action-button action-secondary"
                                title="Edit mapping configuration"
                            >
                                <span className="action-icon">✏️</span>
                                <span className="action-text">Edit</span>
                            </button>

                            <button
                                onClick={() => onDeleteMapping(mapping.fileMapId)}
                                className="action-button action-danger"
                                title="Delete mapping"
                            >
                                <span className="action-icon">🗑️</span>
                                <span className="action-text">Delete</span>
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Help Text */}
            {!hasFiles && (
                <div className="mapping-help">
                    <details>
                        <summary>What is field mapping?</summary>
                        <div className="help-content">
                            <p>
                                Field mapping tells the system which columns in your transaction files
                                contain specific data like dates, amounts, and descriptions. This is
                                required for CSV files and optional for other formats.
                            </p>
                            <ul>
                                <li><strong>Date Column:</strong> Transaction date</li>
                                <li><strong>Amount Column:</strong> Transaction amount</li>
                                <li><strong>Description Column:</strong> Transaction description</li>
                                <li><strong>Category Column:</strong> Transaction category (optional)</li>
                            </ul>
                        </div>
                    </details>
                </div>
            )}
        </div>
    );
};

export default FieldMappingSection;
