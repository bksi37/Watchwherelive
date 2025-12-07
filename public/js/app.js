document.addEventListener('DOMContentLoaded', () => {
    const zipCodeInput = document.getElementById('zip-code-input');
    const updateBtn = document.getElementById('update-location-btn');
    const locationDisplay = document.getElementById('current-location');
    const scheduleBody = document.getElementById('schedule-body');

    // --- TEMPORARY: Simulate API Data for the MVP Front-End Test ---
    // In production, this data would come from your MongoDB via the Serverless API.
    const MOCK_API_DATA = [
        { 
            date_time: "7:00 PM CST", 
            matchup: "Lakers @ Celtics (NBA)",
            tier1: "ESPN, ESPN+",
            regional_map: {
                "90210": "Spectrum SportsNet",  // LA Area
                "02108": "NBC Sports Boston",  // Boston Area
                "default": "NBA League Pass"
            }
        },
        { 
            date_time: "1:30 PM CST", 
            matchup: "Tottenham vs Chelsea (EPL)",
            tier1: "USA Network, Peacock",
            regional_map: {
                "default": "Peacock Premium"
            }
        },
        { 
            date_time: "9:00 PM CST", 
            matchup: "Warriors @ Suns (NBA)",
            tier1: "NBA TV",
            regional_map: {
                "90210": "NBC Sports Bay Area", // San Francisco area (often blacked out if local)
                "85001": "Suns Live (Local Stream)", // Phoenix area
                "default": "NBA League Pass"
            }
        }
    ];

    let currentZipCode = localStorage.getItem('zipCode') || null;

    // --- Core Logic: Render Schedule ---
    function renderSchedule(zipCode) {
        scheduleBody.innerHTML = '';
        const displayZip = zipCode ? zipCode : 'N/A';
        locationDisplay.textContent = zipCode ? `ZIP: ${zipCode}` : '[Default: US National Feed]';

        MOCK_API_DATA.forEach(game => {
            let localSolution = game.regional_map[zipCode] || game.regional_map['default'];
            
            // Highlight the primary Tier 2 value
            const localHtml = `<span class="local-solution-highlight">${localSolution}</span>`;

            const row = scheduleBody.insertRow();
            
            row.innerHTML = `
                <td>${game.date_time}</td>
                <td>${game.matchup}</td>
                <td>${game.tier1}</td>
                <td class="local-column">${localHtml}</td>
            `;
        });
    }

    // --- Event Handlers ---
    updateBtn.addEventListener('click', () => {
        const inputZip = zipCodeInput.value.trim();
        if (inputZip.length === 5 && !isNaN(inputZip)) {
            currentZipCode = inputZip;
            localStorage.setItem('zipCode', currentZipCode);
            // In production: You would call your Serverless API here with the ZIP code.
            // fetch('/api/schedule?zip=' + inputZip).then(res => res.json()).then(data => renderSchedule(data, inputZip));
            renderSchedule(currentZipCode);
        } else {
            alert('Please enter a valid 5-digit ZIP code.');
        }
    });

    // Load initial schedule on page load
    if (currentZipCode) {
        zipCodeInput.value = currentZipCode;
    }
    renderSchedule(currentZipCode);
});