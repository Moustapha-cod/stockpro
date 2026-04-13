// StockPro SN - Scripts globaux

document.addEventListener('DOMContentLoaded', function() {
    // Validation des formulaires Bootstrap
    const forms = document.querySelectorAll('form.needs-validation');
    
    Array.from(forms).forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
});
