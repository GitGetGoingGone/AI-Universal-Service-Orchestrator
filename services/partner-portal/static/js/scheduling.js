/**
 * Product availability scheduling UI.
 * Renders slots in a week grid with color-coded booking modes.
 * Auto book (green), Check before (amber), Not available (gray).
 */
(function () {
    const MODE_COLORS = {
        auto_book: '#bbf7d0',
        check_before_book: '#fef08a',
        not_available: '#e5e7eb',
    };
    const MODE_LABELS = {
        auto_book: 'Auto book',
        check_before_book: 'Check before',
        not_available: 'Not available',
    };

    window.initScheduling = function (opts) {
        const { container, availability, partnerId, productId, onDelete } = opts || {};
        const el = document.querySelector(container);
        if (!el) return;

        el.innerHTML = '';

        if (!availability || availability.length === 0) {
            el.innerHTML = '<p style="color:var(--color-text-secondary);">No slots yet. Add slots below.</p>';
            return;
        }

        const grid = document.createElement('div');
        grid.className = 'scheduling-grid';
        grid.style.cssText = 'display:grid;grid-template-columns:repeat(7,1fr);gap:4px;margin:8px 0;';

        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        dayNames.forEach(d => {
            const h = document.createElement('div');
            h.style.cssText = 'font-weight:600;padding:4px;font-size:0.9em;';
            h.textContent = d;
            grid.appendChild(h);
        });

        const slotsByDay = {};
        availability.forEach(s => {
            const start = s.start_at ? new Date(s.start_at) : null;
            const day = start ? start.getDay() : 0;
            if (!slotsByDay[day]) slotsByDay[day] = [];
            slotsByDay[day].push(s);
        });

        for (let d = 0; d < 7; d++) {
            const cell = document.createElement('div');
            cell.style.cssText = 'min-height:60px;border:1px solid var(--color-border);border-radius:4px;padding:4px;';
            const daySlots = slotsByDay[d] || [];
            daySlots.forEach(slot => {
                const start = slot.start_at ? new Date(slot.start_at) : null;
                const end = slot.end_at ? new Date(slot.end_at) : null;
                const timeStr = start && end
                    ? start.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + '-' + end.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                    : 'Slot';
                const mode = slot.booking_mode || 'auto_book';
                const block = document.createElement('div');
                block.className = 'scheduling-slot';
                block.style.cssText = `background:${MODE_COLORS[mode] || MODE_COLORS.auto_book};padding:4px;margin:2px 0;border-radius:4px;font-size:0.8em;display:flex;justify-content:space-between;align-items:center;`;
                block.innerHTML = `<span>${timeStr} (${MODE_LABELS[mode] || mode})</span>`;
                if (onDelete && slot.id) {
                    const btn = document.createElement('button');
                    btn.textContent = '×';
                    btn.style.cssText = 'border:none;background:transparent;cursor:pointer;font-size:1.2em;';
                    btn.onclick = () => {
                        if (confirm('Delete this slot?')) onDelete(slot.id);
                    };
                    block.appendChild(btn);
                }
                cell.appendChild(block);
            });
            grid.appendChild(cell);
        }

        el.appendChild(grid);
    };
})();
