// Quick Fix: Remove approve buttons from users who are already approved
// Run this in browser console on the admin/users page

function fixApproveButtons() {
    console.log('🔧 Fixing approve buttons for approved users...');
    
    // Fix desktop table rows
    const desktopRows = document.querySelectorAll('tr.user-row');
    desktopRows.forEach(row => {
        const statusCell = row.querySelector('td:nth-child(2)');
        const actionsCell = row.querySelector('td:last-child');
        
        if (statusCell && actionsCell) {
            const statusText = statusCell.textContent.trim();
            const approveForm = actionsCell.querySelector('.approve-form');
            
            // If user is approved or admin, remove approve button
            if ((statusText.includes('Approved') || statusText.includes('Admin')) && approveForm) {
                console.log('✅ Removing approve button from desktop row (status: ' + statusText + ')');
                approveForm.remove();
            }
        }
    });
    
    // Fix mobile cards
    const mobileCards = document.querySelectorAll('.user-card');
    mobileCards.forEach(card => {
        const statusSpan = card.querySelector('span:last-child');
        const approveForm = card.querySelector('.approve-form');
        
        if (statusSpan && approveForm) {
            const statusText = statusSpan.textContent.trim();
            
            // If user is approved or admin, remove approve button
            if (statusText.includes('Approved') || statusText.includes('Admin')) {
                console.log('✅ Removing approve button from mobile card (status: ' + statusText + ')');
                approveForm.remove();
            }
        }
    });
    
    console.log('🎉 Fix complete! Approve buttons removed from approved/admin users.');
}

// Run the fix
fixApproveButtons();

// Also set up a mutation observer to fix buttons automatically when DOM updates
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
            // Small delay to let DOM settle
            setTimeout(fixApproveButtons, 100);
        }
    });
});

// Start observing
observer.observe(document.getElementById('userTableBody') || document.body, {
    childList: true,
    subtree: true
});

console.log('👀 Set up automatic fix observer for future updates');