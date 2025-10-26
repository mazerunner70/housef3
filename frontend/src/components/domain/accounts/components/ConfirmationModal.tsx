import React from 'react';
import './ConfirmationModal.css'; // Import the CSS file

interface ConfirmationModalProps {
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    onCancel: () => void;
}

const ConfirmationModal: React.FC<ConfirmationModalProps> = ({ isOpen, title, message, onConfirm, onCancel }) => {
    if (!isOpen) {
        return null;
    }

    return (
        <div className="confirmation-modal-backdrop">
            <div className="confirmation-modal-content">
                <h2>{title}</h2>
                <p>{message}</p>
                <div className="confirmation-modal-actions">
                    {/* Apply specific class for confirm button if needed for more specific styling beyond generic button */}
                    <button onClick={onConfirm} className="confirm-button">Confirm</button>
                    {/* Apply specific class for cancel button */}
                    <button onClick={onCancel} className="cancel-button-modal">Cancel</button>
                </div>
            </div>
        </div>
    );
};

export default ConfirmationModal;
