import React, { useEffect } from 'react';
import { useNavigationStore } from '@/stores/navigationStore';
import TransfersDashboard from './TransfersDashboard';
import './TransfersPage.css';

const TransfersPage: React.FC = () => {
    const { goToTransfers } = useNavigationStore();

    // Set up correct breadcrumb for transfers page
    useEffect(() => {
        goToTransfers();
    }, [goToTransfers]);

    return (
        <div className="transfers-page">
            <TransfersDashboard />
        </div>
    );
};

export default TransfersPage;
