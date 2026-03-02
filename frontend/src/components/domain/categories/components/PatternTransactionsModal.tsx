/**
 * Pattern Transactions Modal Component
 * 
 * Displays transactions that were matched to a recurring charge pattern.
 * Domain component specific to category management.
 */

import React, { useEffect, useRef, useState } from 'react';
import type { Transaction } from '@/types/Transaction';
import { getPatternTransactions } from '@/services/RecurringChargeService';
import { formatAmount, formatDate } from '@/types/RecurringCharge';
import './PatternTransactionsModal.css';

export interface PatternTransactionsModalProps {
    isOpen: boolean;
    patternId: string | null;
    merchantPattern: string;
    onClose: () => void;
}

const PatternTransactionsModal: React.FC<PatternTransactionsModalProps> = ({
    isOpen,
    patternId,
    merchantPattern,
    onClose
}) => {
    const modalRef = useRef<HTMLDivElement>(null);
    const closeButtonRef = useRef<HTMLButtonElement>(null);
    const previousActiveElementRef = useRef<HTMLElement | null>(null);
    
    const [transactions, setTransactions] = useState<Transaction[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Fetch transactions when modal opens
    useEffect(() => {
        if (isOpen && patternId) {
            loadTransactions();
        }
    }, [isOpen, patternId]);

    const loadTransactions = async () => {
        if (!patternId) return;
        
        setIsLoading(true);
        setError(null);
        
        try {
            const response = await getPatternTransactions(patternId);
            setTransactions(response.transactions);
        } catch (err) {
            console.error('Error loading pattern transactions:', err);
            setError('Failed to load transactions. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    // Focus management
    useEffect(() => {
        if (isOpen) {
            previousActiveElementRef.current = document.activeElement as HTMLElement;
            setTimeout(() => {
                closeButtonRef.current?.focus();
            }, 100);
        } else {
            if (previousActiveElementRef.current) {
                previousActiveElementRef.current.focus();
            }
        }
    }, [isOpen]);

    // Focus trap
    useEffect(() => {
        if (!isOpen) return;

        const handleTabKey = (e: KeyboardEvent) => {
            if (e.key !== 'Tab') return;

            const modal = modalRef.current;
            if (!modal) return;

            const focusableElements = modal.querySelectorAll<HTMLElement>(
                'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
            );
            const firstElement = focusableElements[0];
            const lastElement = focusableElements[focusableElements.length - 1];

            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    e.preventDefault();
                    lastElement?.focus();
                }
            } else {
                if (document.activeElement === lastElement) {
                    e.preventDefault();
                    firstElement?.focus();
                }
            }
        };

        document.addEventListener('keydown', handleTabKey);
        return () => document.removeEventListener('keydown', handleTabKey);
    }, [isOpen]);

    if (!isOpen) return null;

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Escape') {
            onClose();
        }
    };

    return (
        <div
            className="pattern-transactions-modal-overlay"
            onClick={handleOverlayClick}
            onKeyDown={handleKeyDown}
            role="presentation"
        >
            <div
                ref={modalRef}
                className="pattern-transactions-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="pattern-transactions-modal-title"
            >
                <div className="pattern-transactions-modal-header">
                    <h3 id="pattern-transactions-modal-title">
                        Matched Transactions: {merchantPattern}
                    </h3>
                    <button
                        ref={closeButtonRef}
                        className="close-btn"
                        onClick={onClose}
                        aria-label="Close dialog"
                    >
                        ×
                    </button>
                </div>

                <div className="pattern-transactions-modal-body">
                    {isLoading && (
                        <div className="loading-state">
                            <div className="spinner" aria-label="Loading transactions"></div>
                            <p>Loading transactions...</p>
                        </div>
                    )}

                    {error && (
                        <div className="error-state">
                            <p className="error-message">{error}</p>
                            <button onClick={loadTransactions} className="retry-btn">
                                Retry
                            </button>
                        </div>
                    )}

                    {!isLoading && !error && transactions.length === 0 && (
                        <div className="empty-state">
                            <p>No transactions found for this pattern.</p>
                        </div>
                    )}

                    {!isLoading && !error && transactions.length > 0 && (
                        <>
                            <div className="transactions-summary">
                                <p>{transactions.length} transaction{transactions.length !== 1 ? 's' : ''} matched</p>
                            </div>
                            
                            <div className="transactions-list">
                                <table className="transactions-table">
                                    <thead>
                                        <tr>
                                            <th>Date</th>
                                            <th>Description</th>
                                            <th>Amount</th>
                                            <th>Account</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {transactions.map((tx) => (
                                            <tr key={tx.transactionId}>
                                                <td className="date-cell">
                                                    {tx.date ? formatDate(tx.date) : '-'}
                                                </td>
                                                <td className="description-cell">
                                                    {tx.description || '-'}
                                                </td>
                                                <td className="amount-cell">
                                                    {tx.amount !== undefined ? formatAmount(tx.amount) : '-'}
                                                </td>
                                                <td className="account-cell">
                                                    {tx.accountId || '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>

                <div className="pattern-transactions-modal-footer">
                    <button
                        className="close-footer-btn"
                        onClick={onClose}
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
};

export default PatternTransactionsModal;

