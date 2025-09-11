// UI Module - Handles all UI updates and interactions
const UI = {
    // Format currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-US', CONFIG.formatting.currency).format(amount);
    },

    // Format number
    formatNumber(num, decimals = 1) {
        return num.toFixed(decimals);
    },

    // Format percentage
    formatPercentage(decimal) {
        return new Intl.NumberFormat('en-US', CONFIG.formatting.percentage).format(decimal);
    },

    // Create input field HTML
    createInputField(config) {
        const tooltipAttr = config.tooltip ? `class="tooltip" data-tooltip="${config.tooltip}"` : '';
        const note = config.note ? `<div class="small-text" style="color: #27ae60; margin-top: 5px;">${config.note}</div>` : '';
        const inputType = config.type || 'number';
        const required = config.required ? 'required' : '';
        
        if (inputType === 'text') {
            return `
                <div class="input-group">
                    <label for="${config.id}" ${tooltipAttr}>${config.label}</label>
                    <input type="text" 
                           id="${config.id}" 
                           value="${CONFIG.defaults[config.id] || ''}" 
                           ${required}
                           placeholder="${config.placeholder || ''}">
                    ${note}
                </div>
            `;
        } else {
            return `
                <div class="input-group">
                    <label for="${config.id}" ${tooltipAttr}>${config.label}</label>
                    <input type="number" 
                           id="${config.id}" 
                           value="${CONFIG.defaults[config.id] || 0}" 
                           min="${config.min || 0}" 
                           max="${config.max || 999999}"
                           step="${config.step || 1}">
                    ${note}
                </div>
            `;
        }
    },

    // Initialize input sections
    initializeInputs() {
        // Project Information
        const projectInfo = document.getElementById('project-info');
        if (projectInfo) {
            CONFIG.inputs.projectInfo.forEach(input => {
                projectInfo.innerHTML += this.createInputField(input);
            });
        }

        // Team Configuration
        const teamConfig = document.getElementById('team-config');
        if (teamConfig) {
            CONFIG.inputs.teamConfig.forEach(input => {
                teamConfig.innerHTML += this.createInputField(input);
            });
        }

        // Development Costs
        const devCosts = document.getElementById('dev-costs');
        if (devCosts) {
            CONFIG.inputs.devCosts.forEach(input => {
                devCosts.innerHTML += this.createInputField(input);
            });
        }

        // Manual Process
        const manualProcess = document.getElementById('manual-process');
        if (manualProcess) {
            CONFIG.inputs.manualProcess.forEach(input => {
                manualProcess.innerHTML += this.createInputField(input);
            });
        }

        // Implementation Details
        const implementationDetails = document.getElementById('implementation-details');
        if (implementationDetails) {
            CONFIG.inputs.implementationDetails.forEach(input => {
                implementationDetails.innerHTML += this.createInputField(input);
            });
        }

        // Salary Increases
        const salaryIncreases = document.getElementById('salary-increases');
        if (salaryIncreases) {
            CONFIG.inputs.salaryIncreases.forEach(input => {
                salaryIncreases.innerHTML += this.createInputField(input);
            });
        }
    },

    // Create result item HTML
    createResultItem(config, value) {
        const highlightClass = config.highlight ? 'highlight' : '';
        let formattedValue = value;

        switch(config.format) {
            case 'currency':
                formattedValue = this.formatCurrency(value);
                break;
            case 'number':
                formattedValue = this.formatNumber(value);
                break;
            case 'percentage':
                formattedValue = this.formatPercentage(value);
                break;
            case 'payback':
                formattedValue = `${this.formatNumber(value)} months`;
                break;
        }

        return `
            <div class="result-item ${highlightClass}" id="${config.id}-row">
                <span>${config.label}</span>
                <span class="result-value" id="${config.id}">${formattedValue}</span>
            </div>
        `;
    },

    // Initialize results display
    initializeResults() {
        const resultsContainer = document.getElementById('results-container');
        if (resultsContainer) {
            CONFIG.results.forEach(result => {
                resultsContainer.innerHTML += this.createResultItem(result, 0);
            });
        }
    },

    // Update display with calculated values
    updateDisplay(results) {
        // Update result values
        document.getElementById('hoursSaved').textContent = this.formatNumber(results.summary.hoursSaved);
        document.getElementById('monthlySavingsUser').textContent = this.formatCurrency(results.summary.monthlySavingsUser);
        document.getElementById('errorSavings').textContent = this.formatCurrency(results.summary.errorSavings);
        document.getElementById('monthlyTeamSavings').textContent = this.formatCurrency(results.summary.monthlyTeamSavings);
        document.getElementById('annualSavings').textContent = this.formatCurrency(results.summary.annualSavings);
        document.getElementById('developmentCost').textContent = this.formatCurrency(results.summary.developmentCost);
        document.getElementById('implementationCost').textContent = this.formatCurrency(results.summary.implementationCost);
        document.getElementById('netSavings').textContent = this.formatCurrency(results.summary.netSavings);
        document.getElementById('paybackPeriod').textContent = `${this.formatNumber(results.summary.paybackPeriod)} months`;
        document.getElementById('roi').textContent = this.formatPercentage(results.summary.roi);

        // Update dashboard
        document.getElementById('dashMonthly').textContent = this.formatCurrency(results.summary.monthlyTeamSavings);
        document.getElementById('dashAnnual').textContent = this.formatCurrency(results.summary.annualSavings);
        document.getElementById('dashPayback').textContent = this.formatNumber(results.summary.paybackPeriod);
        document.getElementById('dash5Year').textContent = this.formatCurrency(results.summary.fiveYearBenefit);

        // Update 5-year projection table
        this.updateProjectionTable(results.projection);

        // Color code payback period
        const paybackRow = document.getElementById('paybackPeriod-row');
        if (paybackRow) {
            if (results.summary.paybackPeriod <= 3) {
                paybackRow.className = 'result-item highlight';
            } else if (results.summary.paybackPeriod <= 6) {
                paybackRow.className = 'result-item';
            } else {
                paybackRow.className = 'result-item warning';
            }
        }
    },

    // Update projection table
    updateProjectionTable(projectionData) {
        const tableBody = document.getElementById('projectionTableBody');
        if (!tableBody) return;

        tableBody.innerHTML = '';

        projectionData.projection.forEach(year => {
            const row = tableBody.insertRow();
            const netBenefitColor = year.netBenefit >= 0 ? 'color: #27ae60;' : 'color: #e74c3c;';
            const cumulativeColor = year.cumulativeBenefit >= 0 ? 'color: #27ae60;' : 'color: #e74c3c;';

            row.innerHTML = `
                <td style="padding: 10px;">Year ${year.year}</td>
                <td style="text-align: right; padding: 10px;">${this.formatCurrency(year.savings)}</td>
                <td style="text-align: right; padding: 10px;">${this.formatCurrency(year.costs)}</td>
                <td style="text-align: right; padding: 10px; ${netBenefitColor}">${this.formatCurrency(year.netBenefit)}</td>
                <td style="text-align: right; padding: 10px; font-weight: bold; ${cumulativeColor}">${this.formatCurrency(year.cumulativeBenefit)}</td>
                <td style="text-align: right; padding: 10px; font-weight: bold;">${this.formatPercentage(year.roi)}</td>
            `;
        });

        // Update totals
        document.getElementById('total5YearSavings').textContent = this.formatCurrency(projectionData.total5YearSavings);
        document.getElementById('total5YearCosts').textContent = this.formatCurrency(projectionData.total5YearCosts);
        document.getElementById('total5YearNet').textContent = this.formatCurrency(projectionData.total5YearNet);
        document.getElementById('total5YearCumulative').textContent = this.formatCurrency(projectionData.total5YearCumulative);
        document.getElementById('total5YearROI').textContent = this.formatPercentage(projectionData.total5YearROI);
        document.getElementById('fiveYearBenefit').textContent = this.formatCurrency(projectionData.total5YearCumulative);
    },

    // Show/hide views
    showCalculator() {
        const calculator = document.getElementById('calculator-view');
        const report = document.getElementById('fullReport');
        if (calculator) calculator.style.display = 'block';
        if (report) report.style.display = 'none';
        window.scrollTo(0, 0);
    },

    showReport() {
        const calculator = document.getElementById('calculator-view');
        const report = document.getElementById('fullReport');
        if (calculator) calculator.style.display = 'none';
        if (report) report.style.display = 'block';
        window.scrollTo(0, 0);
    }
};