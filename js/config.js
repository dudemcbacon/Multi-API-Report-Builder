// Configuration and Constants
const CONFIG = {
    // Default Values
    defaults: {
        teamSize: 5,
        hourlyRate: 35,
        devMonths: 3,
        devHoursPerWeek: 40,
        devSalary: 55000,
        manualExport: 12,
        manualRecon: 4,
        manualConsol: 7,
        webstoreClearing: 4,
        tieOut: 4,
        shareFileOps: 8.3,
        automationSetup: 5,
        errorsPerMonth: 18,
        errorCost: 100,
        maintenance: 1000,
        teamSalaryIncrease: 3,
        devSalaryIncrease: 3
    },

    // Input Field Configurations
    inputs: {
        teamConfig: [
            {
                id: 'teamSize',
                label: 'Team Size (users):',
                tooltip: 'Number of people who will use the application',
                min: 1,
                max: 50,
                step: 1
            },
            {
                id: 'hourlyRate',
                label: 'Hourly Rate ($):',
                tooltip: 'Loaded hourly cost including benefits and overhead',
                min: 15,
                max: 100,
                step: 1
            }
        ],
        devCosts: [
            {
                id: 'devMonths',
                label: 'Development Period (months):',
                tooltip: 'Time to develop the solution',
                min: 1,
                max: 12,
                step: 0.5
            },
            {
                id: 'devHoursPerWeek',
                label: 'Hours per Week:',
                tooltip: 'Developer hours per week',
                min: 10,
                max: 60,
                step: 1
            },
            {
                id: 'devSalary',
                label: 'Developer Annual Salary ($):',
                tooltip: 'Annual developer salary',
                min: 30000,
                max: 150000,
                step: 5000
            }
        ],
        manualProcess: [
            {
                id: 'manualExport',
                label: 'Report Formatting:',
                tooltip: 'Time formatting Salesforce reports',
                min: 0,
                max: 100,
                step: 0.5
            },
            {
                id: 'manualRecon',
                label: 'Data Corrections & QBES:',
                tooltip: 'Corrections including QBES items (4 hrs/month)',
                min: 0,
                max: 100,
                step: 0.5
            },
            {
                id: 'manualConsol',
                label: 'WooCommerce Fee Processing:',
                tooltip: 'Adding WooCommerce fees (1.5-2 hrs/week = ~7 hrs/month)',
                min: 0,
                max: 100,
                step: 0.5
            },
            {
                id: 'webstoreClearing',
                label: 'Webstore Clearing Reconciliation:',
                tooltip: 'Month-end webstore clearing reconciliation',
                min: 0,
                max: 100,
                step: 0.5
            },
            {
                id: 'tieOut',
                label: 'Tie-Out Process:',
                tooltip: 'Monthly tie-out process',
                min: 0,
                max: 100,
                step: 0.5
            },
            {
                id: 'shareFileOps',
                label: 'ShareFile Manual Operations:',
                tooltip: 'Manual file saving (~15 min/save) and accessing (~10 min/access) - Est. 20 saves + 30 accesses/month',
                min: 0,
                max: 100,
                step: 0.1
            }
        ],
        implementationDetails: [
            {
                id: 'automationSetup',
                label: 'Automation Setup Time (minutes):',
                tooltip: 'One-time setup to schedule the automated process',
                min: 1,
                max: 60,
                step: 1,
                note: '✓ Fully automated after setup - no ongoing time required'
            },
            {
                id: 'errorsPerMonth',
                label: 'Errors per Month:',
                tooltip: 'Average number of errors in manual processes per month',
                min: 0,
                max: 100,
                step: 1
            },
            {
                id: 'errorCost',
                label: 'Cost per Error ($):',
                tooltip: 'Average cost to identify and fix each error',
                min: 10,
                max: 1000,
                step: 10
            },
            {
                id: 'maintenance',
                label: 'Annual Maintenance ($):',
                tooltip: 'Annual maintenance and support costs',
                min: 0,
                max: 10000,
                step: 100
            }
        ],
        salaryIncreases: [
            {
                id: 'teamSalaryIncrease',
                label: 'Team Salary Increase (%):',
                tooltip: 'Annual salary increase for team members (affects savings in years 2-5)',
                min: 0,
                max: 10,
                step: 0.5
            },
            {
                id: 'devSalaryIncrease',
                label: 'Developer Salary Increase (%):',
                tooltip: 'Annual salary increase for developers (affects maintenance costs in years 2-5)',
                min: 0,
                max: 10,
                step: 0.5
            }
        ]
    },

    // Result Display Configuration
    results: [
        { id: 'hoursSaved', label: 'Hours Saved per User/Month:', format: 'number' },
        { id: 'monthlySavingsUser', label: 'Monthly Labor Savings per User:', format: 'currency' },
        { id: 'errorSavings', label: 'Monthly Error Cost Savings:', format: 'currency' },
        { id: 'monthlyTeamSavings', label: 'Total Monthly Team Savings:', format: 'currency', highlight: true },
        { id: 'annualSavings', label: 'Annual Team Savings:', format: 'currency' },
        { id: 'developmentCost', label: 'Development Cost:', format: 'currency' },
        { id: 'implementationCost', label: 'Total Implementation Cost:', format: 'currency' },
        { id: 'netSavings', label: 'Net Year 1 Savings:', format: 'currency', highlight: true },
        { id: 'paybackPeriod', label: 'Payback Period:', format: 'payback' },
        { id: 'roi', label: 'Year 1 ROI:', format: 'percentage', highlight: true }
    ],

    // Formatting options
    formatting: {
        currency: {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        },
        number: {
            minimumFractionDigits: 1,
            maximumFractionDigits: 1
        },
        percentage: {
            style: 'percent',
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        }
    },

    // ShareFile calculation constants
    shareFile: {
        totalOperations: 50,
        saveOperations: 20,
        accessOperations: 30,
        saveTimeMultiplier: 1.5,
        accessTimeMultiplier: 0.67
    },

    // Development calculation constants
    development: {
        hoursPerYear: 2080, // 52 weeks * 40 hours
        weeksPerMonth: 4.33
    },

    // Projection settings
    projection: {
        years: 5,
        firstMonthProductivity: 0.5 // 50% productivity in first month
    },

    // Local storage key
    storageKey: 'roiCalculatorData'
};