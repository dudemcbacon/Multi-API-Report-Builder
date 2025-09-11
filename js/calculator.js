// Calculator Module - Core calculation logic
const Calculator = {
    // Get all input values
    getInputValues() {
        const values = {};
        const allInputs = document.querySelectorAll('input[type="number"]');
        allInputs.forEach(input => {
            values[input.id] = parseFloat(input.value) || 0;
        });
        return values;
    },

    // Calculate development costs
    calculateDevelopmentCost(inputs) {
        const devHourlyRate = inputs.devSalary / CONFIG.development.hoursPerYear;
        const totalDevHours = inputs.devMonths * (inputs.devHoursPerWeek * CONFIG.development.weeksPerMonth);
        return totalDevHours * devHourlyRate;
    },

    // Calculate time savings
    calculateTimeSavings(inputs) {
        // All manual time is saved with full automation
        return {
            exportSaved: inputs.manualExport,
            reconSaved: inputs.manualRecon,
            consolSaved: inputs.manualConsol,
            webstoreSaved: inputs.webstoreClearing,
            tieOutSaved: inputs.tieOut,
            shareFileSaved: inputs.shareFileOps,
            totalHoursSaved: inputs.manualExport + inputs.manualRecon + 
                           inputs.manualConsol + inputs.webstoreClearing + 
                           inputs.tieOut + inputs.shareFileOps
        };
    },

    // Calculate cost savings
    calculateCostSavings(inputs, timeSavings) {
        const monthlyLaborSavingsUser = timeSavings.totalHoursSaved * inputs.hourlyRate;
        const monthlyLaborSavingsTeam = monthlyLaborSavingsUser * inputs.teamSize;
        const monthlyErrorSavings = inputs.errorsPerMonth * inputs.errorCost;
        const monthlyTeamSavings = monthlyLaborSavingsTeam + monthlyErrorSavings;
        const annualTeamSavings = monthlyTeamSavings * 12;

        return {
            monthlyLaborSavingsUser,
            monthlyLaborSavingsTeam,
            monthlyErrorSavings,
            monthlyTeamSavings,
            annualTeamSavings
        };
    },

    // Calculate ROI metrics
    calculateROI(inputs, developmentCost, costSavings) {
        const totalImplementationCost = developmentCost;
        const netYear1Savings = costSavings.annualTeamSavings - totalImplementationCost - inputs.maintenance;
        const paybackMonths = totalImplementationCost > 0 ? 
                            totalImplementationCost / costSavings.monthlyTeamSavings : 0;
        const year1ROI = totalImplementationCost > 0 ? 
                        netYear1Savings / totalImplementationCost : 0;

        return {
            totalImplementationCost,
            netYear1Savings,
            paybackMonths,
            year1ROI
        };
    },

    // Calculate 5-year projection
    calculate5YearProjection(inputs, timeSavings, costSavings, roi) {
        const projection = [];
        let cumulativeBenefit = 0;
        let total5YearSavings = 0;
        let total5YearCosts = 0;

        // Track adjusted rates for compound growth
        let currentTeamHourlyRate = inputs.hourlyRate;
        let currentMaintenance = inputs.maintenance;

        for (let year = 1; year <= CONFIG.projection.years; year++) {
            // Apply salary increases starting from year 2
            if (year > 1) {
                currentTeamHourlyRate = currentTeamHourlyRate * (1 + inputs.teamSalaryIncrease / 100);
                currentMaintenance = currentMaintenance * (1 + inputs.devSalaryIncrease / 100);
            }

            // Calculate year-specific savings with adjusted hourly rate
            const yearLaborSavingsUser = timeSavings.totalHoursSaved * currentTeamHourlyRate;
            const yearLaborSavingsTeam = yearLaborSavingsUser * inputs.teamSize * 12;
            const yearErrorSavings = inputs.errorsPerMonth * inputs.errorCost * 12;
            const yearSavings = yearLaborSavingsTeam + yearErrorSavings;

            // Calculate year-specific costs
            const yearCosts = year === 1 ? 
                            roi.totalImplementationCost + inputs.maintenance : 
                            currentMaintenance;

            const netBenefit = yearSavings - yearCosts;
            cumulativeBenefit += netBenefit;
            const yearROI = roi.totalImplementationCost > 0 ? 
                          (cumulativeBenefit / roi.totalImplementationCost) : 0;

            total5YearSavings += yearSavings;
            total5YearCosts += yearCosts;

            projection.push({
                year,
                savings: yearSavings,
                costs: yearCosts,
                netBenefit,
                cumulativeBenefit,
                roi: yearROI
            });
        }

        return {
            projection,
            total5YearSavings,
            total5YearCosts,
            total5YearNet: total5YearSavings - total5YearCosts,
            total5YearCumulative: cumulativeBenefit,
            total5YearROI: roi.totalImplementationCost > 0 ? 
                         cumulativeBenefit / roi.totalImplementationCost : 0
        };
    },

    // Main calculation function
    calculate() {
        const inputs = this.getInputValues();
        const developmentCost = this.calculateDevelopmentCost(inputs);
        const timeSavings = this.calculateTimeSavings(inputs);
        const costSavings = this.calculateCostSavings(inputs, timeSavings);
        const roi = this.calculateROI(inputs, developmentCost, costSavings);
        const projection = this.calculate5YearProjection(inputs, timeSavings, costSavings, roi);

        return {
            inputs,
            developmentCost,
            timeSavings,
            costSavings,
            roi,
            projection,
            summary: {
                hoursSaved: timeSavings.totalHoursSaved,
                monthlySavingsUser: costSavings.monthlyLaborSavingsUser,
                errorSavings: costSavings.monthlyErrorSavings,
                monthlyTeamSavings: costSavings.monthlyTeamSavings,
                annualSavings: costSavings.annualTeamSavings,
                developmentCost: developmentCost,
                implementationCost: roi.totalImplementationCost,
                netSavings: roi.netYear1Savings,
                paybackPeriod: roi.paybackMonths,
                roi: roi.year1ROI,
                fiveYearBenefit: projection.total5YearCumulative
            }
        };
    }
};