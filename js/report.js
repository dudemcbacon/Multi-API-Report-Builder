// Report Module - Handles report generation
const Report = {
    // Generate the full report
    generate(results) {
        const reportContent = document.getElementById('report-content');
        if (!reportContent) return;

        const reportHTML = this.buildReportHTML(results);
        reportContent.innerHTML = reportHTML;
        UI.showReport();
    },

    // Build the report HTML
    buildReportHTML(results) {
        const { inputs, timeSavings, costSavings, roi, projection } = results;
        
        // Calculate additional report metrics
        const totalManualHours = (inputs.manualExport + inputs.manualRecon + inputs.manualConsol + 
                                 inputs.webstoreClearing + inputs.tieOut + inputs.shareFileOps) * inputs.teamSize;
        const totalAutoHours = 0; // Fully automated
        const hoursSavedMonthly = totalManualHours;
        const hoursSavedAnnually = hoursSavedMonthly * 12;
        const timeReductionPercent = 100; // 100% reduction - fully automated

        const monthlyMaintenance = inputs.maintenance / 12;
        const month1Savings = costSavings.monthlyTeamSavings * CONFIG.projection.firstMonthProductivity;
        const month1Net = month1Savings - roi.totalImplementationCost;
        const monthlyROI = roi.totalImplementationCost > 0 ? costSavings.monthlyTeamSavings / roi.totalImplementationCost : 0;

        const strategicHours = hoursSavedMonthly;
        const opportunityValueLow = strategicHours * 50;
        const opportunityValueHigh = strategicHours * 75;

        // Calculate ShareFile time details
        const totalMinutesPerMonth = inputs.shareFileOps * 60;
        const averageMinutesPerOperation = totalMinutesPerMonth / CONFIG.shareFile.totalOperations;
        const saveMinutes = Math.round(averageMinutesPerOperation * CONFIG.shareFile.saveTimeMultiplier);
        const accessMinutes = Math.round(averageMinutesPerOperation * CONFIG.shareFile.accessTimeMultiplier);

        // Get recommendation text based on ROI
        let recommendationText;
        if (roi.year1ROI > 3.0) {
            recommendationText = "With exceptional ROI exceeding 300%, this application represents an outstanding investment opportunity that should be implemented immediately.";
        } else if (roi.year1ROI > 1.0) {
            recommendationText = "With strong ROI exceeding 100%, this application represents a high-value investment that should be prioritized for immediate deployment.";
        } else if (roi.year1ROI > 0.5) {
            recommendationText = "With positive ROI and reasonable payback period, this application represents a solid investment opportunity.";
        } else {
            recommendationText = "Based on current parameters, consider adjusting assumptions or exploring implementation optimizations to improve ROI.";
        }

        return `
            <button class="print-button" onclick="app.showCalculator()">← Back to Calculator</button>
            
            <h1>Sales Receipt Import Automation - ROI Analysis Report</h1>

            <h2>Executive Summary</h2>
            <p>The Sales Receipt Import Automation is a multi-API data integration that delivers significant ROI through
                automation of financial operations, reduction in manual data processing, and elimination of errors in
                reconciliation tasks. This customized analysis is based on your specific organizational parameters.</p>

            <div class="metrics-box">
                <h3>Key ROI Metrics</h3>
                <ul>
                    <li><strong>${UI.formatNumber(timeReductionPercent, 0)}%</strong> reduction in total processing time</li>
                    <li><strong>${UI.formatCurrency(costSavings.monthlyTeamSavings)}</strong> monthly team savings</li>
                    <li><strong>${UI.formatCurrency(costSavings.annualTeamSavings)}</strong> annual team savings</li>
                    <li><strong>${UI.formatNumber(roi.paybackMonths, 1)}</strong> month payback period</li>
                    <li><strong>${UI.formatPercentage(roi.year1ROI)}</strong> Year 1 ROI</li>
                </ul>
            </div>

            <h2>Detailed ROI Analysis</h2>

            <h3>1. Time Savings Analysis</h3>
            <h4>Current Manual Process (Monthly)</h4>
            <ul>
                <li><strong>Data Export/Import:</strong> ${UI.formatNumber(inputs.manualExport, 1)} hours/month × ${inputs.teamSize} users = ${UI.formatNumber(inputs.manualExport * inputs.teamSize, 1)} team hours</li>
                <li><strong>Data Reconciliation:</strong> ${UI.formatNumber(inputs.manualRecon, 1)} hours/month × ${inputs.teamSize} users = ${UI.formatNumber(inputs.manualRecon * inputs.teamSize, 1)} team hours</li>
                <li><strong>Multi-source Consolidation:</strong> ${UI.formatNumber(inputs.manualConsol, 1)} hours/month × ${inputs.teamSize} users = ${UI.formatNumber(inputs.manualConsol * inputs.teamSize, 1)} team hours</li>
                <li><strong>Webstore Clearing Reconciliation:</strong> ${UI.formatNumber(inputs.webstoreClearing, 1)} hours/month × ${inputs.teamSize} users = ${UI.formatNumber(inputs.webstoreClearing * inputs.teamSize, 1)} team hours</li>
                <li><strong>Tie-Out Process:</strong> ${UI.formatNumber(inputs.tieOut, 1)} hours/month × ${inputs.teamSize} users = ${UI.formatNumber(inputs.tieOut * inputs.teamSize, 1)} team hours</li>
                <li><strong>ShareFile Manual Operations:</strong> ${UI.formatNumber(inputs.shareFileOps, 1)} hours/month × ${inputs.teamSize} users = ${UI.formatNumber(inputs.shareFileOps * inputs.teamSize, 1)} team hours</li>
                <li><strong>Total Manual Hours:</strong> ${UI.formatNumber(totalManualHours, 1)} hours/month</li>
            </ul>

            <h4>Automated Process</h4>
            <ul>
                <li><strong>Process Type:</strong> Fully automated scheduled workflow</li>
                <li><strong>Setup Time:</strong> ${inputs.automationSetup} minutes (one-time)</li>
                <li><strong>Report Formatting:</strong> Fully automated</li>
                <li><strong>Data Corrections & QBES:</strong> Fully automated</li>
                <li><strong>WooCommerce Fee Processing:</strong> Fully automated</li>
                <li><strong>Webstore Clearing Reconciliation:</strong> Fully automated</li>
                <li><strong>Tie-Out Process:</strong> Fully automated</li>
                <li><strong>ShareFile Operations:</strong> Automated with consistent naming conventions</li>
                <li><strong>Human Intervention Required:</strong> None after initial setup</li>
                <li><strong>Total Ongoing Hours:</strong> 0 hours/month</li>
            </ul>

            <h4>Time Savings Calculation</h4>
            <ul>
                <li><strong>Hours Saved Monthly:</strong> ${UI.formatNumber(hoursSavedMonthly, 1)} hours</li>
                <li><strong>Hours Saved Annually:</strong> ${UI.formatNumber(hoursSavedAnnually, 1)} hours</li>
                <li><strong>Time Reduction Percentage:</strong> ${UI.formatNumber(timeReductionPercent, 0)}%</li>
            </ul>

            <h3>2. Cost Savings Analysis</h3>
            <h4>Labor Cost Savings</h4>
            <ul>
                <li><strong>Hourly Rate:</strong> ${UI.formatCurrency(inputs.hourlyRate)}</li>
                <li><strong>Monthly Labor Savings:</strong> ${UI.formatCurrency(costSavings.monthlyLaborSavingsTeam)}</li>
                <li><strong>Annual Labor Savings:</strong> ${UI.formatCurrency(costSavings.monthlyLaborSavingsTeam * 12)}</li>
            </ul>

            <h4>Error Reduction Value</h4>
            <ul>
                <li><strong>Current Error Rate:</strong> ${inputs.errorsPerMonth} errors/month</li>
                <li><strong>Cost per Error:</strong> ${UI.formatCurrency(inputs.errorCost)}</li>
                <li><strong>Monthly Error Cost Avoided:</strong> ${UI.formatCurrency(costSavings.monthlyErrorSavings)}</li>
                <li><strong>Annual Error Cost Avoided:</strong> ${UI.formatCurrency(costSavings.monthlyErrorSavings * 12)}</li>
            </ul>

            <h3>3. Implementation Costs</h3>
            <h4>Development Costs</h4>
            <ul>
                <li><strong>Development Period:</strong> ${UI.formatNumber(inputs.devMonths, 1)} months</li>
                <li><strong>Developer Hours per Week:</strong> ${inputs.devHoursPerWeek} hours</li>
                <li><strong>Total Development Hours:</strong> ${UI.formatNumber(inputs.devMonths * inputs.devHoursPerWeek * CONFIG.development.weeksPerMonth, 0)} hours</li>
                <li><strong>Developer Hourly Rate:</strong> ${UI.formatCurrency(inputs.devSalary / CONFIG.development.hoursPerYear)}</li>
                <li><strong>Total Development Cost:</strong> ${UI.formatCurrency(results.developmentCost)}</li>
            </ul>

            <h4>Implementation Costs</h4>
            <ul>
                <li><strong>Total Implementation Cost:</strong> ${UI.formatCurrency(roi.totalImplementationCost)}</li>
            </ul>

            <h4>Ongoing Costs</h4>
            <ul>
                <li><strong>Annual Maintenance:</strong> ${UI.formatCurrency(inputs.maintenance)}</li>
                <li><strong>Monthly Maintenance:</strong> ${UI.formatCurrency(monthlyMaintenance)}</li>
            </ul>

            <h3>4. ROI Timeline</h3>
            <h4>Month 1</h4>
            <ul>
                <li>Implementation and training costs: -${UI.formatCurrency(roi.totalImplementationCost)}</li>
                <li>Partial productivity gains (50%): ${UI.formatCurrency(month1Savings)}</li>
                <li><strong>Net Month 1:</strong> ${UI.formatCurrency(month1Net)}</li>
            </ul>

            <h4>Months 2-12</h4>
            <ul>
                <li>Full monthly savings: ${UI.formatCurrency(costSavings.monthlyTeamSavings)}</li>
                <li>Monthly ROI (after payback): ${UI.formatPercentage(monthlyROI)}</li>
            </ul>

            <h4>Year 1 Summary</h4>
            <ul>
                <li><strong>Total Annual Savings:</strong> ${UI.formatCurrency(costSavings.annualTeamSavings)}</li>
                <li><strong>Total Costs:</strong> ${UI.formatCurrency(roi.totalImplementationCost + inputs.maintenance)}</li>
                <li><strong>Net Year 1 Benefit:</strong> ${UI.formatCurrency(roi.netYear1Savings)}</li>
                <li><strong>Year 1 ROI:</strong> ${UI.formatPercentage(roi.year1ROI)}</li>
            </ul>

            <h2>Productivity Impact Analysis</h2>
            <h3>Staff Reallocation Benefits</h3>
            <ul>
                <li><strong>Hours freed for strategic work:</strong> ${UI.formatNumber(strategicHours, 1)} hours/month</li>
                <li><strong>Value of strategic work:</strong> $50-75/hour (estimated)</li>
                <li><strong>Monthly opportunity value:</strong> ${UI.formatCurrency(opportunityValueLow)} - ${UI.formatCurrency(opportunityValueHigh)}</li>
            </ul>

            <h3>Scalability Benefits</h3>
            <ul>
                <li>Process 100,000+ rows automatically</li>
                <li>No additional time for 10x data volume increase</li>
                <li>Fully automated - runs unattended on schedule</li>
                <li>Supports business growth without any staff increase</li>
                <li>Eliminates all manual processing time</li>
                <li>Zero overtime costs - runs 24/7 if needed</li>
            </ul>

            <h3>ShareFile Automation Benefits</h3>
            <ul>
                <li><strong>Automated File Naming:</strong> Consistent naming conventions applied automatically</li>
                <li><strong>Automatic Upload:</strong> Reports saved directly to ShareFile without manual intervention</li>
                <li><strong>Version Control:</strong> Automatic versioning and audit trail</li>
                <li><strong>Time Saved:</strong> ~${saveMinutes} minutes per file save, ~${accessMinutes} minutes per file retrieval</li>
                <li><strong>Monthly Impact:</strong> Eliminates ${UI.formatNumber(inputs.shareFileOps, 1)} hours of manual file management</li>
                <li><strong>Error Reduction:</strong> No more misfiled or misnamed reports</li>
                <li><strong>Instant Access:</strong> Team members can access reports immediately after generation</li>
            </ul>

            <h2>Risk Mitigation</h2>
            <h3>Operational Risks Eliminated</h3>
            <ul>
                <li><strong>Manual error risk:</strong> Eliminated through automation</li>
                <li><strong>Key person dependency:</strong> Process documented and automated</li>
                <li><strong>Data loss risk:</strong> Automated backups and audit trails</li>
                <li><strong>Compliance risk:</strong> Consistent rule application</li>
            </ul>

            <h3>Financial Risk Reduction</h3>
            <ul>
                <li><strong>Revenue leakage:</strong> Caught through automated reconciliation</li>
                <li><strong>Error correction costs:</strong> Reduced by 95%</li>
                <li><strong>Audit findings:</strong> Significantly reduced through automated processes</li>
            </ul>

            <h2>Competitive Advantages</h2>
            <h3>Speed to Insight</h3>
            <ul>
                <li><strong>5x faster</strong> financial reporting</li>
                <li><strong>Same-day</strong> sales receipt import vs. 3-5 days</li>
                <li><strong>Real-time</strong> problem identification</li>
            </ul>

            <h3>Business Agility</h3>
            <ul>
                <li>Handle <strong>10x data volume</strong> without additional staff</li>
                <li>Support business growth without proportional cost increase</li>
                <li>Enable new business models through automation</li>
            </ul>

            <h2>5-Year Financial Projection</h2>
            <p><em>Note: Projections include ${inputs.teamSalaryIncrease}% annual team salary
                    increases and ${inputs.devSalaryIncrease}% annual developer salary increases
                    starting in Year 2.</em></p>
            ${this.buildProjectionTable(projection)}

            <h2>Implementation Recommendation</h2>
            <div class="metrics-box">
                <p>Based on your specific parameters, the Sales Receipt Import Automation delivers:</p>
                <ul>
                    <li><strong>Immediate monthly savings:</strong> ${UI.formatCurrency(costSavings.monthlyTeamSavings)}</li>
                    <li><strong>Annual savings:</strong> ${UI.formatCurrency(costSavings.annualTeamSavings)}</li>
                    <li><strong>Payback period:</strong> ${UI.formatNumber(roi.paybackMonths, 1)} months</li>
                    <li><strong>Year 1 ROI:</strong> ${UI.formatPercentage(roi.year1ROI)}</li>
                </ul>
            </div>

            <h3>Investment Decision</h3>
            <p>${recommendationText}</p>

            <h2>Appendix: Calculation Parameters</h2>
            <h3>Your Organization's Assumptions</h3>
            <ul>
                <li><strong>Team Size:</strong> ${inputs.teamSize} users</li>
                <li><strong>Hourly Rate:</strong> ${UI.formatCurrency(inputs.hourlyRate)} (loaded cost)</li>
                <li><strong>Current Manual Hours:</strong> ${UI.formatNumber(totalManualHours, 1)} hours/month total</li>
                <li><strong>Automated Hours:</strong> ${totalAutoHours} hours/month total</li>
                <li><strong>Error Rate:</strong> ${inputs.errorsPerMonth} errors/month @ ${UI.formatCurrency(inputs.errorCost)} each</li>
                <li><strong>Implementation Cost:</strong> ${UI.formatCurrency(roi.totalImplementationCost)} total</li>
                <li><strong>Team Salary Increase:</strong> ${inputs.teamSalaryIncrease}% annually (Years 2-5)</li>
                <li><strong>Developer Salary Increase:</strong> ${inputs.devSalaryIncrease}% annually (Years 2-5)</li>
            </ul>

            <hr>
            <p><em>This ROI analysis is based on your specific organizational parameters entered on ${new Date().toLocaleDateString()}.
                   Actual results may vary based on implementation execution and operational factors.</em></p>
        `;
    },

    // Build projection table HTML
    buildProjectionTable(projectionData) {
        let tableHTML = `
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <thead>
                    <tr style="background: #ecf0f1;">
                        <th style="padding: 10px; text-align: left; border: 1px solid #bdc3c7;">Year</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #bdc3c7;">Savings</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #bdc3c7;">Costs</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #bdc3c7;">Net Benefit</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #bdc3c7;">Cumulative</th>
                        <th style="padding: 10px; text-align: right; border: 1px solid #bdc3c7;">ROI</th>
                    </tr>
                </thead>
                <tbody>
        `;

        projectionData.projection.forEach(year => {
            const netBenefitColor = year.netBenefit >= 0 ? 'color: #27ae60;' : 'color: #e74c3c;';
            tableHTML += `
                <tr>
                    <td style="padding: 8px; border: 1px solid #bdc3c7;">Year ${year.year}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7;">${UI.formatCurrency(year.savings)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7;">${UI.formatCurrency(year.costs)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7; ${netBenefitColor}">${UI.formatCurrency(year.netBenefit)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7; font-weight: bold;">${UI.formatCurrency(year.cumulativeBenefit)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7; font-weight: bold;">${UI.formatPercentage(year.roi)}</td>
                </tr>
            `;
        });

        tableHTML += `
                <tr style="background: #ecf0f1; font-weight: bold;">
                    <td style="padding: 8px; border: 1px solid #bdc3c7;">5-Year Total</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7;">${UI.formatCurrency(projectionData.total5YearSavings)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7;">${UI.formatCurrency(projectionData.total5YearCosts)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7; color: #27ae60;">${UI.formatCurrency(projectionData.total5YearNet)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7; color: #27ae60;">${UI.formatCurrency(projectionData.total5YearCumulative)}</td>
                    <td style="padding: 8px; text-align: right; border: 1px solid #bdc3c7;">${UI.formatPercentage(projectionData.total5YearROI)}</td>
                </tr>
            </tbody>
        </table>
        `;

        return tableHTML;
    }
};