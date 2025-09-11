// Main Application Module
const app = {
    // Initialize the application
    init() {
        console.log('Initializing ROI Calculator Application...');
        
        // Initialize UI components
        UI.initializeInputs();
        UI.initializeResults();
        
        // Load saved data if available
        this.loadSavedData();
        
        // Attach event listeners
        this.attachEventListeners();
        
        // Perform initial calculation
        this.performCalculation();
        
        console.log('Application initialized successfully');
    },

    // Attach event listeners to all inputs
    attachEventListeners() {
        const inputs = document.querySelectorAll('input[type="number"]');
        inputs.forEach(input => {
            input.addEventListener('input', () => {
                this.performCalculation();
                this.saveData();
            });
        });
    },

    // Perform calculation and update display
    performCalculation() {
        const results = Calculator.calculate();
        UI.updateDisplay(results);
        this.currentResults = results; // Store for report generation
    },

    // Save input data to localStorage
    saveData() {
        const inputs = document.querySelectorAll('input[type="number"]');
        const data = {};
        inputs.forEach(input => {
            data[input.id] = input.value;
        });
        localStorage.setItem(CONFIG.storageKey, JSON.stringify(data));
    },

    // Load saved data from localStorage
    loadSavedData() {
        const saved = localStorage.getItem(CONFIG.storageKey);
        if (saved) {
            try {
                const data = JSON.parse(saved);
                Object.keys(data).forEach(id => {
                    const input = document.getElementById(id);
                    if (input) {
                        input.value = data[id];
                    }
                });
                console.log('Loaded saved data from localStorage');
            } catch (error) {
                console.error('Error loading saved data:', error);
            }
        }
    },

    // Generate full report
    generateReport() {
        if (!this.currentResults) {
            this.performCalculation();
        }
        Report.generate(this.currentResults);
    },

    // Print generated report
    printGeneratedReport() {
        // Generate report first to ensure it's up to date
        this.generateReport();
        
        // Add printing class to body for proper print styling
        document.body.classList.add('printing-report');
        
        // Wait a moment for the report to render, then print
        setTimeout(() => {
            window.print();
            
            // Remove the printing class after printing
            setTimeout(() => {
                document.body.classList.remove('printing-report');
            }, 100);
        }, 100);
    },

    // Show calculator view
    showCalculator() {
        UI.showCalculator();
    },

    // Store current results
    currentResults: null
};

// Initialize the application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    app.init();
});