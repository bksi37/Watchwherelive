document.addEventListener('DOMContentLoaded', () => {
    const unvalidatedSection = document.getElementById('unvalidated-games-section');
    const dmaMapSection = document.getElementById('dma-map-section');
    const navButtons = document.querySelectorAll('.nav-button');
    const unvalidatedBody = document.getElementById('unvalidated-body');
    const dmaMapBody = document.getElementById('dma-map-body');
    
    // --- TEMPORARY MOCK DATA (In production: this comes from your Serverless API) ---
    const MOCK_UNVALIDATED_GAMES = [
        // NBA Lakers game needs RSN mapping
        { id: 'LAL_BOS_Dec10', sport: 'NBA', away: 'Lakers', home: 'Celtics', 
          tier1: 'NBA TV', placeholder: 'RSN / Blackout Check', status: 'Unmapped', date: 'Dec 10' },
        // NBA Jazz game needs RSN mapping
        { id: 'UTA_PHX_Dec11', sport: 'NBA', away: 'Jazz', home: 'Suns', 
          tier1: 'League Pass', placeholder: 'RSN / Blackout Check', status: 'Unmapped', date: 'Dec 11' },
    ];
    
    const MOCK_DMA_MAP = [
        { dma: 'LA-DMA', team: 'LAL', sport: 'NBA', channel: 'Spectrum SportsNet', status: 'Active' },
        { dma: 'BOS-DMA', team: 'BOS', sport: 'NBA', channel: 'NBC Sports Boston', status: 'Active' },
        { dma: 'CHI-DMA', team: 'CHI', sport: 'NBA', channel: 'NBC Sports Chicago', status: 'Active' },
    ];
    // --------------------------------------------------------------------------

    // --- Tab Switching Logic ---
    function switchTab(targetId) {
        unvalidatedSection.classList.add('hidden');
        dmaMapSection.classList.add('hidden');
        
        navButtons.forEach(btn => btn.classList.remove('active'));

        if (targetId === 'nav-unvalidated') {
            unvalidatedSection.classList.remove('hidden');
            document.getElementById('nav-unvalidated').classList.add('active');
            renderUnvalidatedGames(MOCK_UNVALIDATED_GAMES);
        } else if (targetId === 'nav-dma-map') {
            dmaMapSection.classList.remove('hidden');
            document.getElementById('nav-dma-map').classList.add('active');
            renderDmaMap(MOCK_DMA_MAP);
        }
    }

    navButtons.forEach(button => {
        button.addEventListener('click', () => switchTab(button.id));
    });

    // --- Render Unvalidated Games ---
    function renderUnvalidatedGames(games) {
        document.getElementById('unvalidated-count').textContent = games.length;
        unvalidatedBody.innerHTML = '';
        games.forEach(game => {
            const row = unvalidatedBody.insertRow();
            row.innerHTML = `
                <td>${game.id}</td>
                <td>${game.away} @ ${game.home} (${game.sport})</td>
                <td>${game.tier1}</td>
                <td class="highlight-column">
                    <input type="text" value="${game.placeholder}" placeholder="Enter RSN/Blackout Rule" class="edit-input" data-game-id="${game.id}">
                </td>
                <td>
                    <button class="save-btn" data-game-id="${game.id}">Approve/Map</button>
                </td>
            `;
            // NOTE: In the real app, "Approve/Map" would trigger the Layer 2 processing.
        });
    }

    // --- Render DMA/RSN Map ---
    function renderDmaMap(mapping) {
        dmaMapBody.innerHTML = '';
        mapping.forEach((rule, index) => {
            const row = dmaMapBody.insertRow();
            row.id = `rule-${index}`;
            row.innerHTML = `
                <td><input type="text" value="${rule.dma}" class="edit-input" data-field="dma"></td>
                <td><input type="text" value="${rule.team}" class="edit-input" data-field="team"></td>
                <td><input type="text" value="${rule.sport}" class="edit-input" data-field="sport"></td>
                <td><input type="text" value="${rule.channel}" class="edit-input" data-field="channel"></td>
                <td>
                    <button class="save-btn" data-rule-id="${index}">Save</button>
                    <button class="delete-btn" data-rule-id="${index}">Delete</button>
                </td>
            `;
        });
    }
    
    // --- Initial Load ---
    switchTab('nav-unvalidated');
    document.getElementById('last-run').textContent = new Date().toLocaleString();
    
    // NOTE: Event listeners for 'Save' and 'Add New Mapping' would be implemented here,
    // which would call a secure PUT/POST endpoint on your Serverless API.
    
    // Example event listener placeholder for the Save button on the DMA map (CRITICAL for Layer 2)
    document.getElementById('dma-map-table').addEventListener('click', (e) => {
        if (e.target.classList.contains('save-btn')) {
            const ruleId = e.target.getAttribute('data-rule-id');
            console.log(`Simulating save for rule ID: ${ruleId}`);
            // TO-DO: Implement Fetch POST request to Serverless API here
        }
    });
});