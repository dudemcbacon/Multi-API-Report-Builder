# ROI Calculator

A professional web application for calculating the Return on Investment (ROI) of Sales Receipt Import Automation projects. This tool provides comprehensive financial analysis including cost-benefit calculations, payback period analysis, and 5-year projections.

## Features

- **Interactive ROI Calculations** - Real-time calculations as you input parameters
- **Comprehensive Analysis** - Covers development costs, time savings, error reduction, and operational benefits
- **5-Year Projections** - Long-term financial forecasting with salary increase adjustments
- **Professional Reports** - Generate detailed PDF-ready reports for stakeholders
- **Print Functionality** - Print summary or full detailed reports
- **Data Persistence** - Automatically saves your inputs locally
- **Responsive Design** - Works on desktop, tablet, and mobile devices

## Live Demo

Open `index.html` in any modern web browser to start using the calculator.

## Project Structure

```
ROI Calculator/
├── index.html          # Main application entry point
├── css/
│   ├── styles.css      # Main application styles
│   └── print.css       # Print-specific styles
├── js/
│   ├── app.js          # Main application controller
│   ├── calculator.js   # Core calculation logic
│   ├── config.js       # Configuration and constants
│   ├── report.js       # Report generation
│   └── ui.js           # User interface management
└── README.md           # This file
```

## Getting Started

### Prerequisites

- Any modern web browser (Chrome, Firefox, Safari, Edge)
- No server or installation required

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/QuiQuig/ROI-Calculator-.git
   cd ROI-Calculator-
   ```

2. **Open in browser:**
   - Double-click `index.html`
   - Or open your browser and navigate to the file

### Usage

1. **Input Parameters:**
   - Configure your team size and hourly rates
   - Enter development costs and timeline
   - Specify current manual process times
   - Set error rates and maintenance costs

2. **View Results:**
   - Real-time ROI calculations update as you type
   - Review the executive summary dashboard
   - Analyze the 5-year financial projection

3. **Generate Reports:**
   - Click "Generate Full Report" for detailed analysis
   - Use "Print Summary" for quick overview
   - Use "Print Generated Report" for comprehensive documentation

## Key Calculations

### Time Savings
- Calculates hours saved per user/month through automation
- Accounts for elimination of manual processes:
  - Report formatting
  - Data corrections and QBES
  - WooCommerce fee processing
  - Webstore clearing reconciliation
  - Tie-out processes
  - ShareFile manual operations

### Cost Analysis
- **Labor Savings:** Hourly rate × time saved × team size
- **Error Reduction:** Number of errors × cost per error
- **Development Costs:** Developer time × hourly rate
- **Ongoing Costs:** Annual maintenance and support

### ROI Metrics
- **Payback Period:** Time to recover implementation costs
- **Year 1 ROI:** (Annual savings - costs) / implementation cost
- **5-Year Projection:** Long-term financial impact with salary adjustments

## Customization

### Modifying Default Values
Edit `js/config.js` to change default input values:

```javascript
defaults: {
    teamSize: 5,
    hourlyRate: 35,
    devMonths: 3,
    // ... other defaults
}
```

### Adding New Input Fields
1. Add field configuration to `CONFIG.inputs` in `config.js`
2. The UI will automatically generate the input field
3. Update calculation logic in `calculator.js` if needed

### Styling
- Modify `css/styles.css` for appearance changes
- Update `css/print.css` for print layout adjustments
- CSS custom properties in `:root` control theme colors

## Browser Compatibility

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Data Privacy

- All data is stored locally in your browser
- No information is sent to external servers
- Data persists between sessions using localStorage

## Contributing

This is a private project. For suggestions or issues, please contact the project owner.

## License

This project is proprietary software. All rights reserved.

## Support

For questions or support, please contact the development team.

---

**Built for:** Sales Receipt Import Automation ROI Analysis  
**Technology:** Vanilla HTML5, CSS3, JavaScript (ES6+)  
**Version:** 1.0.0