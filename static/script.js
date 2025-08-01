// PhiloQuote - Main JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips if any
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });

    // Enhanced form validation
    const forms = document.querySelectorAll('form[data-validate="true"]');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            if (!form.checkValidity()) {
                e.preventDefault();
                e.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // File upload preview for admin
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const fileInfo = document.createElement('small');
                fileInfo.className = 'text-muted d-block mt-1';
                fileInfo.textContent = `Selected: ${file.name} (${formatFileSize(file.size)})`;
                
                // Remove existing file info
                const existingInfo = fileInput.parentNode.querySelector('.file-info');
                if (existingInfo) {
                    existingInfo.remove();
                }
                
                fileInfo.classList.add('file-info');
                fileInput.parentNode.appendChild(fileInfo);
            }
        });
    }

    // Enhanced textarea auto-resize
    function autoResizeTextarea(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 300) + 'px';
    }

    document.querySelectorAll('textarea').forEach(textarea => {
        // Initial resize
        autoResizeTextarea(textarea);
        
        // Resize on input
        textarea.addEventListener('input', function() {
            autoResizeTextarea(this);
        });
        
        // Resize on focus (in case content was programmatically changed)
        textarea.addEventListener('focus', function() {
            autoResizeTextarea(this);
        });
    });

    // Keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // Ctrl/Cmd + Enter to submit forms in textareas
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            const activeElement = document.activeElement;
            if (activeElement.tagName === 'TEXTAREA') {
                const form = activeElement.closest('form');
                if (form) {
                    form.submit();
                }
            }
        }
        
        // Escape to close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                if (modal) {
                    modal.hide();
                }
            }
        }
    });

    // Loading states for buttons
    function setButtonLoading(button, loading = true) {
        if (loading) {
            button.disabled = true;
            button.dataset.originalText = button.innerHTML;
            button.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Loading...';
        } else {
            button.disabled = false;
            button.innerHTML = button.dataset.originalText || button.innerHTML;
        }
    }

    // Enhanced fetch with error handling
    window.fetchWithErrorHandling = function(url, options = {}) {
        return fetch(url, options)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                console.error('Fetch error:', error);
                showNotification('An error occurred. Please try again.', 'error');
                throw error;
            });
    };

    // Overlay notification for Flask flash messages
    const flaskAlerts = document.querySelectorAll('.alert-flask');
    flaskAlerts.forEach(function(alert) {
        const type = alert.dataset.category || 'info';
        const message = alert.innerText;
        showNotification(message, type);
        alert.remove();
    });

    // Share Quote Button functionality
    const shareBtn = document.getElementById('share-quote-btn');
    if (shareBtn) {
        shareBtn.addEventListener('click', function() {
            const quoteText = document.querySelector('.quote-text')?.innerText?.trim() || '';
            let quoteAuthor = document.querySelector('.quote-author')?.innerText?.trim() || '';
            // Remove leading dash and whitespace from author if present
            quoteAuthor = quoteAuthor.replace(/^[-–—\s]+/, '');
            const shareContent = `"${quoteText}." -${quoteAuthor}`;
            if (navigator.share) {
                navigator.share({
                    title: 'Quote of the Day',
                    text: shareContent
                }).catch(() => {});
            } else {
                navigator.clipboard.writeText(shareContent).then(() => {
                    window.showNotification('Quote copied to clipboard!', 'success');
                }, () => {
                    window.showNotification('Could not copy quote.', 'error');
                });
            }
        });
    }
});

// Notification system (overlay)
window.showNotification = function(message, type = 'info') {
    let container = document.getElementById('overlay-notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'overlay-notification-container';
        document.body.appendChild(container);
    }
    const alertDiv = document.createElement('div');
    alertDiv.className = `overlay-alert alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    container.appendChild(alertDiv);
    setTimeout(() => {
        const alert = bootstrap.Alert.getOrCreateInstance(alertDiv);
        if (alert) alert.close();
    }, 4000);
};

// Service Worker registration (for potential offline functionality)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Note: Service worker file would need to be created separately
        // navigator.serviceWorker.register('/sw.js')
        //     .then(function(registration) {
        //         console.log('SW registered: ', registration);
        //     })
        //     .catch(function(registrationError) {
        //         console.log('SW registration failed: ', registrationError);
        //     });
    });
}
