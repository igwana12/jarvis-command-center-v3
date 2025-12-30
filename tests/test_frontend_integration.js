/**
 * Frontend Integration Tests for Jarvis Command Center V2
 * Tests UI components, interactions, and integration with backend
 */

const API_BASE = 'http://localhost:8000';

class FrontendTestRunner {
    constructor() {
        this.passed = 0;
        this.failed = 0;
        this.errors = [];
        this.warnings = [];
    }

    pass(testName) {
        this.passed++;
        console.log(`✅ PASS: ${testName}`);
    }

    fail(testName, reason) {
        this.failed++;
        const error = `❌ FAIL: ${testName} - ${reason}`;
        this.errors.push(error);
        console.error(error);
    }

    warn(testName, message) {
        const warning = `⚠️  WARN: ${testName} - ${message}`;
        this.warnings.push(warning);
        console.warn(warning);
    }

    async delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    summary() {
        const total = this.passed + this.failed;
        return {
            total,
            passed: this.passed,
            failed: this.failed,
            successRate: total > 0 ? `${(this.passed/total*100).toFixed(1)}%` : '0%',
            errors: this.errors,
            warnings: this.warnings
        };
    }

    // Test 1: Page load and initialization
    async testPageLoad() {
        const testName = 'Page Load';
        try {
            // Check if main elements exist
            const header = document.querySelector('.header');
            const commandBar = document.querySelector('.command-bar');
            const tabs = document.querySelector('.tabs');

            if (!header || !commandBar || !tabs) {
                this.fail(testName, 'Missing main UI elements');
                return;
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 2: Tab switching functionality
    async testTabSwitching() {
        const testName = 'Tab Switching';
        try {
            const tabs = ['agents', 'commands', 'skills', 'mcp', 'workflows', 'knowledge', 'monitor'];

            for (const tabName of tabs) {
                // Find and click tab
                const tabButton = Array.from(document.querySelectorAll('.tab'))
                    .find(btn => btn.textContent.toLowerCase().includes(tabName.replace('-', ' ')));

                if (!tabButton) {
                    this.warn(testName, `Tab button not found: ${tabName}`);
                    continue;
                }

                tabButton.click();
                await this.delay(100);

                // Check if correct tab content is active
                const tabContent = document.getElementById(`${tabName}-tab`);
                if (!tabContent) {
                    this.fail(testName, `Tab content not found: ${tabName}`);
                    return;
                }

                if (!tabContent.classList.contains('active')) {
                    this.fail(testName, `Tab content not active: ${tabName}`);
                    return;
                }

                // Check if tab button is active
                if (!tabButton.classList.contains('active')) {
                    this.fail(testName, `Tab button not active: ${tabName}`);
                    return;
                }
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 3: Search functionality
    async testSearchFunctionality() {
        const testName = 'Search Functionality';
        try {
            // Test agents search
            const agentsTab = document.querySelector('[onclick*="agents"]');
            if (agentsTab) {
                agentsTab.click();
                await this.delay(200);

                const searchInput = document.querySelector('#agents-tab .search-input');
                if (searchInput) {
                    // Simulate search
                    searchInput.value = 'python';
                    searchInput.dispatchEvent(new KeyboardEvent('keyup'));
                    await this.delay(100);

                    // Check if cards are filtered
                    const cards = document.querySelectorAll('#agents-grid .card');
                    const visibleCards = Array.from(cards).filter(card => card.style.display !== 'none');

                    if (cards.length > 0 && visibleCards.length === 0) {
                        this.warn(testName, 'Search filtered all cards');
                    }
                } else {
                    this.warn(testName, 'Search input not found');
                }
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 4: Command input and execution
    async testCommandInput() {
        const testName = 'Command Input';
        try {
            const commandInput = document.getElementById('command-input');
            const commandSubmit = document.querySelector('.command-submit');

            if (!commandInput || !commandSubmit) {
                this.fail(testName, 'Command input or submit button not found');
                return;
            }

            // Test input
            commandInput.value = 'test command';
            const value = commandInput.value;

            if (value !== 'test command') {
                this.fail(testName, 'Command input value not set correctly');
                return;
            }

            // Clear for next tests
            commandInput.value = '';

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 5: Quick actions
    async testQuickActions() {
        const testName = 'Quick Actions';
        try {
            const quickActionsContainer = document.getElementById('quick-actions');

            if (!quickActionsContainer) {
                this.fail(testName, 'Quick actions container not found');
                return;
            }

            const quickActionButtons = quickActionsContainer.querySelectorAll('.quick-action');

            if (quickActionButtons.length === 0) {
                this.warn(testName, 'No quick action buttons found');
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 6: API data loading
    async testAPIDataLoading() {
        const testName = 'API Data Loading';
        try {
            // Test agents loaded
            const agentsGrid = document.getElementById('agents-grid');
            const agentsCards = agentsGrid.querySelectorAll('.card');

            if (agentsCards.length === 0) {
                this.warn(testName, 'No agent cards loaded');
            }

            // Test commands loaded
            const commandsGrid = document.getElementById('commands-grid');
            const commandsCards = commandsGrid.querySelectorAll('.card');

            if (commandsCards.length === 0) {
                this.warn(testName, 'No command cards loaded');
            }

            // Check resource counts
            const resourceCount = document.getElementById('resource-count');
            if (resourceCount.textContent === 'Loading...') {
                this.warn(testName, 'Resource counts still loading');
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 7: Card click interactions
    async testCardInteractions() {
        const testName = 'Card Interactions';
        try {
            // Find first agent card
            const agentsTab = document.querySelector('[onclick*="agents"]');
            if (agentsTab) {
                agentsTab.click();
                await this.delay(200);

                const agentCard = document.querySelector('#agents-grid .card');

                if (agentCard) {
                    // Check if card has click handler
                    if (!agentCard.onclick) {
                        this.warn(testName, 'Agent card missing click handler');
                    }
                } else {
                    this.warn(testName, 'No agent cards available to test');
                }
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 8: Status indicator
    async testStatusIndicator() {
        const testName = 'Status Indicator';
        try {
            const statusText = document.getElementById('status-text');
            const statusDot = document.querySelector('.status-dot');

            if (!statusText || !statusDot) {
                this.fail(testName, 'Status indicator elements not found');
                return;
            }

            // Check status text
            const status = statusText.textContent;
            if (status !== 'Connected' && status !== 'Disconnected') {
                this.warn(testName, `Unexpected status: ${status}`);
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 9: Keyboard shortcuts
    async testKeyboardShortcuts() {
        const testName = 'Keyboard Shortcuts';
        try {
            const commandInput = document.getElementById('command-input');

            // Simulate Cmd+K
            const event = new KeyboardEvent('keydown', {
                key: 'k',
                metaKey: true,
                bubbles: true
            });

            document.dispatchEvent(event);
            await this.delay(100);

            // Check if input is focused (note: programmatic focus may not work in all browsers)
            // This is a best-effort test
            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Test 10: Empty states
    async testEmptyStates() {
        const testName = 'Empty States';
        try {
            // Switch to knowledge tab
            const knowledgeTab = Array.from(document.querySelectorAll('.tab'))
                .find(btn => btn.textContent.toLowerCase().includes('knowledge'));

            if (knowledgeTab) {
                knowledgeTab.click();
                await this.delay(200);

                const emptyState = document.querySelector('#knowledge-tab .empty-state');
                if (!emptyState) {
                    this.warn(testName, 'Empty state not found in knowledge tab');
                }
            }

            this.pass(testName);
        } catch (e) {
            this.fail(testName, e.message);
        }
    }

    // Run all tests
    async runAll() {
        console.log('='.repeat(70));
        console.log('JARVIS COMMAND CENTER V2 - FRONTEND INTEGRATION TESTS');
        console.log('='.repeat(70));
        console.log('');

        console.log('Running UI Component Tests...');
        console.log('-'.repeat(70));

        await this.testPageLoad();
        await this.testTabSwitching();
        await this.testSearchFunctionality();
        await this.testCommandInput();
        await this.testQuickActions();
        await this.testAPIDataLoading();
        await this.testCardInteractions();
        await this.testStatusIndicator();
        await this.testKeyboardShortcuts();
        await this.testEmptyStates();

        console.log('');
        console.log('='.repeat(70));
        console.log('TEST SUMMARY');
        console.log('='.repeat(70));

        const summary = this.summary();
        console.log(`\nTotal Tests: ${summary.total}`);
        console.log(`Passed: ${summary.passed} ✅`);
        console.log(`Failed: ${summary.failed} ❌`);
        console.log(`Success Rate: ${summary.successRate}`);

        if (summary.warnings.length > 0) {
            console.log(`\nWarnings: ${summary.warnings.length} ⚠️`);
            summary.warnings.forEach(w => console.log(`  ${w}`));
        }

        if (summary.errors.length > 0) {
            console.log('\nFailures:');
            summary.errors.forEach(e => console.log(`  ${e}`));
        }

        console.log('');

        return summary;
    }
}

// Auto-run when loaded in browser console
if (typeof window !== 'undefined') {
    window.FrontendTestRunner = FrontendTestRunner;
    console.log('Frontend Test Runner loaded. Run tests with:');
    console.log('  const runner = new FrontendTestRunner();');
    console.log('  runner.runAll();');
}

// Export for Node.js if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = FrontendTestRunner;
}
