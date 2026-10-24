import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Activity, ArrowRight, ArrowUpRight, Bookmark, Bot, BriefcaseBusiness,
  Check, ChevronDown, CircleHelp, Clock3, Compass, Filter, GraduationCap,
  LayoutDashboard, LoaderCircle, MapPin, Menu, MessageCircle, Search, Send, Settings2,
  ShieldCheck, Sparkles, Target, Trash2, TrendingUp, UserRound, WandSparkles, X,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';
const USER_ID = 'demo-user';

const NAV_ITEMS = [
  { id: 'overview', label: 'Overview', icon: LayoutDashboard },
  { id: 'discover', label: 'Discover jobs', icon: Compass, badge: 'Explore' },
  { id: 'agent', label: 'AI career agent', icon: Bot, badge: 'AI' },
  { id: 'saved', label: 'Saved jobs', icon: Bookmark },
  { id: 'profile', label: 'My profile', icon: UserRound },
];

const INITIAL_PROFILE = {
  name: 'Alex Morgan', headline: 'CS student building AI-powered products', skills: ['Python', 'FastAPI', 'SQL', 'REST APIs', 'LLMs', 'React'],
  target_roles: ['AI Engineer Intern', 'Software Engineer Intern', 'Backend Engineer Intern'],
  preferred_locations: ['Bengaluru', 'Gurugram'], work_modes: ['Remote', 'Hybrid'], min_salary: 30000,
  experience_level: 'Internship / Entry-level', dealbreakers: [], notes: 'Interested in early-stage product teams and practical AI engineering.',
};

async function api(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
  const data = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data?.detail || data?.message || `Request failed (${response.status})`);
  return data;
}

function splitList(value) {
  return value.split(',').map((item) => item.trim()).filter(Boolean);
}

function initials(text = 'CP') {
  return text.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join('').toUpperCase();
}

function App() {
  const [page, setPage] = useState('overview');
  const [profile, setProfile] = useState(INITIAL_PROFILE);
  const [jobs, setJobs] = useState([]);
  const [savedJobs, setSavedJobs] = useState([]);
  const [stats, setStats] = useState({ total_jobs: 0, matching_jobs: 0, saved_jobs: 0, skills_count: 0 });
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatMode, setChatMode] = useState('demo');
  const [searchText, setSearchText] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [modeFilter, setModeFilter] = useState('');
  const [profileForm, setProfileForm] = useState(INITIAL_PROFILE);
  const [loading, setLoading] = useState(true);
  const [chatLoading, setChatLoading] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [toast, setToast] = useState('');
  const [apiError, setApiError] = useState('');
  const [selectedJob, setSelectedJob] = useState(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const refreshCore = useCallback(async () => {
    const [profileData, jobsData, savedData, statsData] = await Promise.all([
      api('/profile'), api('/jobs?limit=100'), api('/saved-jobs'), api('/stats'),
    ]);
    setProfile(profileData);
    setProfileForm({
      ...profileData,
      skills: (profileData.skills || []).join(', '),
      target_roles: (profileData.target_roles || []).join(', '),
      preferred_locations: (profileData.preferred_locations || []).join(', '),
      work_modes: (profileData.work_modes || []).join(', '),
      dealbreakers: (profileData.dealbreakers || []).join(', '),
    });
    setJobs(jobsData.items || []);
    setSavedJobs(savedData.items || []);
    setStats(statsData);
    setApiError('');
  }, []);

  useEffect(() => {
    let active = true;
    async function loadApp() {
      try {
        await refreshCore();
        const history = await api('/chat/history');
        if (active) setChatMessages((history || []).map((item) => ({ role: item.role, content: item.content })));
      } catch (error) {
        if (active) setApiError(`${error.message}. Start the FastAPI backend and refresh this page.`);
      } finally {
        if (active) setLoading(false);
      }
    }
    loadApp();
    return () => { active = false; };
  }, [refreshCore]);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(() => setToast(''), 2800);
    return () => window.clearTimeout(timer);
  }, [toast]);

  const savedIds = useMemo(() => new Set(savedJobs.map((job) => job.id)), [savedJobs]);
  const filteredJobs = useMemo(() => {
    return jobs.filter((job) => {
      const text = `${job.title} ${job.company} ${job.location} ${job.required_skills.join(' ')}`.toLowerCase();
      const matchesText = !searchText.trim() || text.includes(searchText.toLowerCase().trim());
      const matchesLocation = !locationFilter || job.location.toLowerCase().includes(locationFilter.toLowerCase());
      const matchesMode = !modeFilter || job.work_mode.toLowerCase() === modeFilter.toLowerCase();
      return matchesText && matchesLocation && matchesMode;
    });
  }, [jobs, searchText, locationFilter, modeFilter]);

  const navigate = (nextPage) => {
    setPage(nextPage);
    setMobileNavOpen(false);
  };

  async function toggleSave(job) {
    const wasSaved = savedIds.has(job.id);
    try {
      if (wasSaved) await api(`/jobs/${job.id}/save`, { method: 'DELETE' });
      else await api(`/jobs/${job.id}/save`, { method: 'POST' });
      await refreshCore();
      setToast(wasSaved ? 'Removed from your saved jobs' : 'Job saved to your shortlist');
    } catch (error) {
      setToast(error.message);
    }
  }

  async function submitProfile(event) {
    event.preventDefault();
    setSavingProfile(true);
    const payload = {
      name: profileForm.name,
      headline: profileForm.headline,
      skills: Array.isArray(profileForm.skills) ? profileForm.skills : splitList(profileForm.skills),
      target_roles: Array.isArray(profileForm.target_roles) ? profileForm.target_roles : splitList(profileForm.target_roles),
      preferred_locations: Array.isArray(profileForm.preferred_locations) ? profileForm.preferred_locations : splitList(profileForm.preferred_locations),
      work_modes: Array.isArray(profileForm.work_modes) ? profileForm.work_modes : splitList(profileForm.work_modes),
      min_salary: profileForm.min_salary === '' || profileForm.min_salary == null ? null : Number(profileForm.min_salary),
      experience_level: profileForm.experience_level,
      dealbreakers: Array.isArray(profileForm.dealbreakers) ? profileForm.dealbreakers : splitList(profileForm.dealbreakers),
      notes: profileForm.notes,
    };
    try {
      const result = await api('/profile', { method: 'PUT', body: JSON.stringify(payload) });
      setProfile(result);
      await refreshCore();
      setToast('Your career profile has been updated');
    } catch (error) {
      setToast(error.message);
    } finally {
      setSavingProfile(false);
    }
  }

  async function sendChat(event, preset = '') {
    event?.preventDefault?.();
    const message = (preset || chatInput).trim();
    if (!message || chatLoading) return;
    const optimistic = [...chatMessages, { role: 'user', content: message }];
    setChatMessages(optimistic);
    setChatInput('');
    setChatLoading(true);
    try {
      const result = await api('/chat', { method: 'POST', body: JSON.stringify({ message, user_id: USER_ID }) });
      setChatMessages((current) => [...current, { role: 'assistant', content: result.reply }]);
      setChatMode(result.mode || 'demo');
      await refreshCore();
    } catch (error) {
      setChatMessages((current) => [...current, { role: 'assistant', content: `I couldn't reach the backend: ${error.message}. Please check that the API is running.` }]);
    } finally {
      setChatLoading(false);
    }
  }

  async function clearConversation() {
    try {
      await api('/chat/history', { method: 'DELETE' });
      setChatMessages([]);
      setToast('Conversation history cleared');
    } catch (error) {
      setToast(error.message);
    }
  }

  function updateForm(field, value) {
    setProfileForm((current) => ({ ...current, [field]: value }));
  }

  const pageTitle = NAV_ITEMS.find((item) => item.id === page)?.label || 'Overview';

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileNavOpen ? 'sidebar-open' : ''}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Sparkles size={21} strokeWidth={2.5} /></div>
          <div><div className="brand-name">careerpilot<span>.</span></div><div className="brand-caption">YOUR AI CAREER AGENT</div></div>
          <button className="icon-button sidebar-close" aria-label="Close navigation" onClick={() => setMobileNavOpen(false)}><X size={18} /></button>
        </div>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          {NAV_ITEMS.map(({ id, label, icon: Icon, badge }) => (
            <button className={`nav-link ${page === id ? 'nav-link-active' : ''}`} key={id} onClick={() => navigate(id)}>
              <Icon size={18} strokeWidth={1.9} />
              <span>{label}</span>
              {badge && <span className={`nav-badge ${badge === 'AI' ? 'nav-badge-ai' : ''}`}>{badge}</span>}
              {id === 'saved' && savedJobs.length > 0 && <span className="nav-count">{savedJobs.length}</span>}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-tip">
            <div className="tip-icon"><WandSparkles size={17} /></div>
            <div className="tip-title">Make your next move count</div>
            <p>Your preferences help surface roles that fit your goals.</p>
            <button onClick={() => navigate('profile')}>Tune your profile <ArrowRight size={14} /></button>
          </div>
          <div className="sidebar-user">
            <div className="avatar avatar-sidebar">{initials(profile.name)}</div>
            <div className="sidebar-user-copy"><strong>{profile.name || 'Your profile'}</strong><span>{profile.headline || 'Career explorer'}</span></div>
            <button className="icon-button user-settings" aria-label="Open profile" onClick={() => navigate('profile')}><Settings2 size={16} /></button>
          </div>
          <div className="sidebar-footnote"><span className="status-dot" /> Demo workspace <span>v1.0</span></div>
        </div>
      </aside>

      {mobileNavOpen && <button className="mobile-scrim" aria-label="Close menu" onClick={() => setMobileNavOpen(false)} />}

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileNavOpen(true)}><Menu size={19} /></button>
            <div className="breadcrumbs"><span>Workspace</span><span className="breadcrumb-slash">/</span><strong>{pageTitle}</strong></div>
          </div>
          <div className="topbar-actions">
            <div className={`api-status ${apiError ? 'api-status-error' : ''}`}><span className="status-dot" />{apiError ? 'API disconnected' : 'System operational'}</div>
            <button className="topbar-help" onClick={() => navigate('agent')}><CircleHelp size={17} /><span>Help</span></button>
            <button className="avatar avatar-top" aria-label="Open profile" onClick={() => navigate('profile')}>{initials(profile.name)}</button>
          </div>
        </header>

        <div className="page-content">
          {apiError && <div className="error-banner"><Activity size={18} /><div><strong>Backend connection needed</strong><span>{apiError}</span></div><button className="text-button" onClick={() => window.location.reload()}>Retry</button></div>}
          {loading ? <LoadingView /> : (
            <>
              {page === 'overview' && <OverviewPage profile={profile} stats={stats} jobs={jobs} savedIds={savedIds} onNavigate={navigate} onSave={toggleSave} onOpenJob={setSelectedJob} />}
              {page === 'discover' && <DiscoverPage jobs={filteredJobs} searchText={searchText} setSearchText={setSearchText} locationFilter={locationFilter} setLocationFilter={setLocationFilter} modeFilter={modeFilter} setModeFilter={setModeFilter} savedIds={savedIds} onSave={toggleSave} onOpenJob={setSelectedJob} />}
              {page === 'agent' && <AgentPage profile={profile} messages={chatMessages} input={chatInput} setInput={setChatInput} loading={chatLoading} mode={chatMode} onSend={sendChat} onClear={clearConversation} onReviewProfile={() => navigate('profile')} onPreset={(text) => sendChat(null, text)} />}
              {page === 'saved' && <SavedPage jobs={savedJobs} onSave={toggleSave} onOpenJob={setSelectedJob} onDiscover={() => navigate('discover')} />}
              {page === 'profile' && <ProfilePage form={profileForm} updateForm={updateForm} onSubmit={submitProfile} saving={savingProfile} stats={stats} />}
            </>
          )}
        </div>
        <footer className="page-footer"><span>CareerPilot <span className="footer-dot">·</span> Built to make career discovery more personal</span><span>Demo project <span className="footer-dot">·</span> Sample roles only</span></footer>
      </main>

      {selectedJob && <JobModal job={selectedJob} saved={savedIds.has(selectedJob.id)} onClose={() => setSelectedJob(null)} onSave={() => toggleSave(selectedJob)} />}
      {toast && <div className="toast-message"><Check size={16} />{toast}</div>}
    </div>
  );
}

function LoadingView() {
  return <div className="loading-screen"><div className="loading-logo"><Sparkles size={26} /></div><LoaderCircle className="spin" size={20} /><strong>Preparing your career workspace</strong><span>Loading profile, job matches, and saved roles…</span></div>;
}

function SectionHeading({ eyebrow, title, subtitle, action, onAction }) {
  return <div className="section-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action && <button className="button button-ghost button-small" onClick={onAction}>{action}<ArrowRight size={15} /></button>}</div>;
}

function StatCard({ label, value, detail, icon: Icon, trend }) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className="stat-icon"><Icon size={18} /></span></div><div className="stat-value">{value}</div><div className="stat-detail">{trend && <span className="stat-trend"><TrendingUp size={13} />{trend}</span>}{detail}</div></div>;
}

function OverviewPage({ profile, stats, jobs, savedIds, onNavigate, onSave, onOpenJob }) {
  const recommended = [...jobs].sort((a, b) => b.match_score - a.match_score).slice(0, 3);
  const profileComplete = [profile.name, profile.headline, (profile.skills || []).length > 0, (profile.target_roles || []).length > 0, (profile.preferred_locations || []).length > 0].filter(Boolean).length;
  const completion = Math.round((profileComplete / 5) * 100);
  const firstName = (profile.name || 'there').trim().split(' ')[0];
  return (
    <div className="page-stack">
      <section className="welcome-row"><div><div className="eyebrow">{new Date().toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" }).toUpperCase()} <span className="eyebrow-dot">·</span> YOUR CAREER DASHBOARD</div><h1>Good to see you, {firstName}<span className="title-period">.</span></h1><p>Let’s find the roles where your skills can make a real impact.</p></div><button className="button button-primary" onClick={() => onNavigate('agent')}><Sparkles size={16} /> Talk to your AI agent <ArrowRight size={16} /></button></section>

      <section className="hero-panel"><div className="hero-orb hero-orb-one" /><div className="hero-orb hero-orb-two" /><div className="hero-content"><div className="hero-kicker"><span className="hero-kicker-dot" /> YOUR NEXT OPPORTUNITY STARTS HERE</div><h2>Great work deserves<br /><span>the right opportunity.</span></h2><p>Your AI career agent is learning what matters to you, so the roles you see become more relevant over time.</p><div className="hero-actions"><button className="button button-light" onClick={() => onNavigate('discover')}>Explore matched roles <ArrowRight size={16} /></button><button className="button button-outline-light" onClick={() => onNavigate('profile')}>Refine my preferences</button></div></div><div className="hero-visual"><div className="orbit orbit-large" /><div className="orbit orbit-small" /><div className="hero-sparkle sparkle-a"><Sparkles size={16} /></div><div className="hero-sparkle sparkle-b"><Target size={17} /></div><div className="hero-center-mark"><Sparkles size={36} /></div><div className="floating-match floating-match-top"><span className="floating-check"><Check size={12} /></span><div><strong>Better fit, less noise</strong><span>Personalized discovery</span></div></div><div className="floating-match floating-match-bottom"><div className="mini-avatar">AI</div><div><strong>CareerPilot agent</strong><span>Ready when you are</span></div><span className="online-pill" /></div></div></section>

      <section className="stats-grid"><StatCard label="Roles in catalogue" value={stats.total_jobs} detail="Curated demo listings" icon={BriefcaseBusiness} /><StatCard label="Potential matches" value={stats.matching_jobs} detail="Score of 55+ / 100" icon={Target} trend="Personalized" /><StatCard label="Saved for later" value={stats.saved_jobs} detail="In your shortlist" icon={Bookmark} /><StatCard label="Skills in profile" value={stats.skills_count} detail="Used to rank roles" icon={GraduationCap} /></section>

      <section className="content-grid overview-grid"><div className="content-main"><SectionHeading eyebrow="CURATED FOR YOU" title="Recommended roles" subtitle="A starting shortlist based on your current profile." action="View all roles" onAction={() => onNavigate('discover')} />{recommended.length ? <div className="job-list">{recommended.map((job) => <JobCard key={job.id} job={job} saved={savedIds.has(job.id)} onSave={onSave} onOpen={onOpenJob} compact />)}</div> : <EmptyState icon={BriefcaseBusiness} title="No matches yet" body="Add a few skills to your profile to improve your recommendations." action="Complete profile" onAction={() => onNavigate('profile')} />}</div><div className="content-side"><div className="side-panel profile-progress-panel"><div className="panel-heading"><div><div className="eyebrow">PROFILE HEALTH</div><h3>Your career profile</h3></div><button className="icon-button" aria-label="Edit profile" onClick={() => onNavigate('profile')}><ArrowUpRight size={17} /></button></div><div className="progress-summary"><div className="progress-ring" style={{ '--progress': `${completion}%` }}><div><strong>{completion}%</strong><span>complete</span></div></div><div className="progress-copy"><strong>{completion >= 80 ? 'Looking good!' : 'A little more detail goes a long way'}</strong><p>A richer profile helps your agent rank jobs more thoughtfully.</p></div></div><div className="checklist"><ChecklistRow done={Boolean(profile.name)} label="Basic details" /><ChecklistRow done={(profile.skills || []).length > 0} label="Add your skills" /><ChecklistRow done={(profile.target_roles || []).length > 0} label="Set target roles" /><ChecklistRow done={(profile.preferred_locations || []).length > 0} label="Choose locations" /></div><button className="button button-dark button-full" onClick={() => onNavigate('profile')}>Update profile <ArrowRight size={15} /></button></div><div className="side-panel agent-promo"><div className="promo-icon"><Bot size={20} /></div><div className="promo-overline">YOUR PERSONAL CAREER AGENT</div><h3>Have a career question?</h3><p>Ask about skills, job fit, or the next step in your search.</p><button className="button button-outline button-full" onClick={() => onNavigate('agent')}>Start a conversation <MessageCircle size={15} /></button></div><div className="demo-note"><ShieldCheck size={16} /><span>This starter uses synthetic job listings. It does not fetch or verify live vacancies.</span></div></div></section>
    </div>
  );
}

function ChecklistRow({ done, label }) {
  return <div className="checklist-row"><span className={`checklist-check ${done ? 'checklist-done' : ''}`}>{done && <Check size={12} />}</span><span className={done ? 'checklist-label-done' : ''}>{label}</span>{done ? <span className="checklist-status">Done</span> : <span className="checklist-status checklist-status-pending">Add</span>}</div>;
}

function DiscoverPage({ jobs, searchText, setSearchText, locationFilter, setLocationFilter, modeFilter, setModeFilter, savedIds, onSave, onOpenJob }) {
  return <div className="page-stack"><SectionHeading eyebrow="OPPORTUNITY EXPLORER" title="Discover your next role" subtitle="Search sample listings ranked against your profile. Match scores are heuristic, not probabilities." /><div className="search-panel"><div className="search-input-wrap"><Search size={18} /><input value={searchText} onChange={(event) => setSearchText(event.target.value)} placeholder="Search roles, skills, or companies…" aria-label="Search jobs" /></div><div className="filter-select-wrap"><MapPin size={16} /><select value={locationFilter} onChange={(event) => setLocationFilter(event.target.value)} aria-label="Filter by location"><option value="">All locations</option><option>Bengaluru</option><option>Gurugram</option><option>Remote</option><option>Pune</option><option>Hyderabad</option></select><ChevronDown size={14} /></div><div className="filter-select-wrap"><Filter size={16} /><select value={modeFilter} onChange={(event) => setModeFilter(event.target.value)} aria-label="Filter by work mode"><option value="">Any work mode</option><option>Remote</option><option>Hybrid</option><option>On-site</option></select><ChevronDown size={14} /></div><button className="button button-dark" onClick={() => { setSearchText(''); setLocationFilter(''); setModeFilter(''); }}>Reset</button></div><div className="result-toolbar"><span><strong>{jobs.length}</strong> roles found</span><div className="sort-pill"><Sparkles size={14} /> Ranked for you</div></div>{jobs.length ? <div className="job-grid">{jobs.map((job) => <JobCard key={job.id} job={job} saved={savedIds.has(job.id)} onSave={onSave} onOpen={onOpenJob} />)}</div> : <EmptyState icon={Search} title="No roles match those filters" body="Try a broader search or clear one of your filters." action="Clear filters" onAction={() => { setSearchText(''); setLocationFilter(''); setModeFilter(''); }} />}</div>;
}

function JobCard({ job, saved, onSave, onOpen, compact = false }) {
  const score = Math.max(0, Math.min(99, job.match_score || 0));
  return <article className={`job-card ${compact ? 'job-card-compact' : ''}`}><div className="job-card-top"><div className={`company-monogram monogram-${job.id % 5}`}>{initials(job.company)}</div><button className={`save-button ${saved ? 'save-button-active' : ''}`} onClick={(event) => { event.stopPropagation(); onSave(job); }} aria-label={saved ? 'Remove saved job' : 'Save job'} title={saved ? 'Remove saved job' : 'Save job'}>{saved ? <Bookmark size={17} fill="currentColor" /> : <Bookmark size={17} />}</button></div><div className="job-title-block"><h3>{job.title}</h3><div className="job-company">{job.company}</div></div><div className="job-meta"><span><MapPin size={13} />{job.location}</span><span><Clock3 size={13} />{job.job_type}</span><span className="work-mode-tag">{job.work_mode}</span></div><p className="job-description">{job.description}</p><div className="skills-row">{(job.required_skills || []).slice(0, compact ? 3 : 4).map((skill) => <span className="skill-chip" key={skill}>{skill}</span>)}{(job.required_skills || []).length > (compact ? 3 : 4) && <span className="skill-more">+{job.required_skills.length - (compact ? 3 : 4)}</span>}</div><div className="job-card-bottom"><div className="match-block"><div className="match-meter"><span style={{ width: `${score}%` }} /></div><div><strong>{score}% match</strong><span>Heuristic fit score</span></div></div><button className="text-button" onClick={() => onOpen(job)}>Details <ArrowUpRight size={14} /></button></div>{!compact && <div className="job-card-id">Demo listing · #{job.id}</div>}</article>;
}

function AgentPage({ profile, messages, input, setInput, loading, mode, onSend, onClear, onReviewProfile, onPreset }) {
  const suggestions = [
    { icon: Search, text: 'Find AI internships in Bengaluru' },
    { icon: WandSparkles, text: 'Which skills should I improve for AI roles?' },
    { icon: Bookmark, text: 'Show my saved jobs' },
    { icon: Target, text: 'I prefer remote only' },
  ];
  return <div className="agent-page-layout"><section className="agent-main"><div className="agent-header"><div className="agent-avatar"><Bot size={23} /></div><div className="agent-header-copy"><div className="eyebrow">CAREERPILOT ASSISTANT</div><h1>Your career, in conversation.</h1><p>Explore roles, update preferences, and plan your next move.</p></div><div className={`agent-mode ${mode === 'openai' ? 'agent-mode-live' : ''}`}><span className="status-dot" />{mode === 'openai' ? 'LLM connected' : mode === 'demo-fallback' ? 'Demo fallback' : 'Demo mode'}</div></div><div className="chat-shell"><div className="chat-scroll-area">{messages.length === 0 ? <div className="chat-welcome"><div className="welcome-orb"><Sparkles size={29} /></div><h2>Hi {(profile?.name || 'there').trim().split(' ')[0]} 👋</h2><p>I can help you explore the sample job catalogue and remember simple career preferences. What would you like to work on?</p><div className="suggestion-grid">{suggestions.map(({ icon: Icon, text }) => <button key={text} className="suggestion-card" onClick={() => onPreset(text)}><Icon size={17} /><span>{text}</span><ArrowUpRight size={14} /></button>)}</div></div> : <div className="chat-thread">{messages.map((message, index) => <ChatBubble key={`${message.role}-${index}`} message={message} />)}{loading && <div className="chat-message assistant-message"><div className="message-avatar"><Bot size={16} /></div><div className="message-bubble typing-bubble"><span /><span /><span /></div></div>}</div>}</div><form className="chat-composer" onSubmit={onSend}><div className="composer-label"><Sparkles size={13} /> Ask CareerPilot</div><textarea value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); onSend(event); } }} placeholder="Tell me what kind of role you're looking for…" rows={2} aria-label="Message CareerPilot" /><div className="composer-bottom"><span>Enter to send <span className="keycap">↵</span><span className="composer-hint"> · Shift + Enter for a new line</span></span><button className="send-button" type="submit" disabled={!input.trim() || loading} aria-label="Send message">{loading ? <LoaderCircle className="spin" size={17} /> : <Send size={17} />}</button></div></form><div className="chat-disclaimer"><ShieldCheck size={14} /> You control your preferences. This starter only uses a local demo profile and sample listings.</div></div></section><aside className="agent-aside"><div className="agent-side-card agent-side-about"><div className="side-card-icon purple-icon"><Sparkles size={18} /></div><h3>What I can help with</h3><div className="agent-capability"><span className="capability-icon"><Search size={15} /></span><div><strong>Find relevant roles</strong><p>Search jobs using your preferences and skills.</p></div></div><div className="agent-capability"><span className="capability-icon"><UserRound size={15} /></span><div><strong>Remember preferences</strong><p>Update skills, locations, and work modes.</p></div></div><div className="agent-capability"><span className="capability-icon"><Bookmark size={15} /></span><div><strong>Build a shortlist</strong><p>Save interesting jobs for another time.</p></div></div></div><div className="agent-side-card agent-side-memory"><div className="memory-head"><div className="side-card-icon green-icon"><Activity size={18} /></div><span className="memory-status"><span className="status-dot" /> Active</span></div><h3>Profile memory</h3><p>Your profile is stored in the local database and used to personalize job matches.</p><div className="memory-chips">{[...(profile?.skills || []).slice(0, 2), ...(profile?.preferred_locations || []).slice(0, 1)].map((skill) => <span key={skill}>{skill}</span>)}</div><button className="text-button" onClick={onReviewProfile}>Review your profile <ArrowRight size={14} /></button></div><div className="agent-side-card agent-side-clear"><div><h3>Want a fresh start?</h3><p>Clear the current conversation. Your saved jobs and preferences will stay.</p></div><button className="icon-button" onClick={onClear} aria-label="Clear conversation"><Trash2 size={17} /></button></div></aside></div>;
}

function ChatBubble({ message }) {
  const isUser = message.role === 'user';
  return <div className={`chat-message ${isUser ? 'user-message' : 'assistant-message'}`}>{!isUser && <div className="message-avatar"><Bot size={16} /></div>}<div className="message-bubble">{message.content.split('\n').map((line, index) => <span className="message-line" key={index}>{line || '\u00a0'}</span>)}</div>{isUser && <div className="message-avatar user-message-avatar"><UserRound size={15} /></div>}</div>;
}

function SavedPage({ jobs, onSave, onOpenJob, onDiscover }) {
  return <div className="page-stack"><SectionHeading eyebrow="YOUR SHORTLIST" title="Saved jobs" subtitle="Keep promising opportunities together while you decide what to pursue." action="Find more roles" onAction={onDiscover} />{jobs.length ? <><div className="saved-summary"><div className="saved-summary-icon"><Bookmark size={18} /></div><div><strong>{jobs.length} {jobs.length === 1 ? 'role' : 'roles'} saved</strong><span>Saved to your local CareerPilot workspace</span></div></div><div className="job-grid">{jobs.map((job) => <JobCard key={job.id} job={job} saved onSave={onSave} onOpen={onOpenJob} />)}</div></> : <EmptyState icon={Bookmark} title="Your shortlist is waiting" body="Save a role that catches your eye and it will appear here." action="Explore roles" onAction={onDiscover} />}</div>;
}

function ProfilePage({ form, updateForm, onSubmit, saving, stats }) {
  const inputFields = [
    { key: 'skills', label: 'Skills', placeholder: 'Python, FastAPI, SQL, React', help: 'Separate skills with commas.' },
    { key: 'target_roles', label: 'Target roles', placeholder: 'AI Engineer Intern, Backend Engineer Intern', help: 'Roles you want your agent to prioritize.' },
    { key: 'preferred_locations', label: 'Preferred locations', placeholder: 'Bengaluru, Gurugram, Remote', help: 'Cities or Remote.' },
    { key: 'work_modes', label: 'Work modes', placeholder: 'Remote, Hybrid', help: 'Use Remote, Hybrid, and/or On-site.' },
    { key: 'dealbreakers', label: 'Deal-breakers', placeholder: 'Unpaid, relocation required', help: 'Listings containing these phrases will be filtered out.' },
  ];
  return <div className="page-stack profile-page"><SectionHeading eyebrow="YOUR CAREER DNA" title="My career profile" subtitle="Your preferences shape job ranking. Keep them current as your goals evolve." /><div className="profile-layout"><form className="profile-form-card" onSubmit={onSubmit}><div className="form-card-heading"><div className="form-heading-icon"><UserRound size={20} /></div><div><h3>Candidate details</h3><p>Tell your career agent what matters to you.</p></div></div><div className="form-grid"><label className="field-label">Full name<input value={form.name || ''} onChange={(event) => updateForm('name', event.target.value)} required placeholder="Your name" /></label><label className="field-label">Experience level<select value={form.experience_level || 'Internship / Entry-level'} onChange={(event) => updateForm('experience_level', event.target.value)}><option>Internship / Entry-level</option><option>New graduate</option><option>0–1 years</option><option>1–3 years</option><option>3+ years</option></select></label><label className="field-label field-full">Headline<input value={form.headline || ''} onChange={(event) => updateForm('headline', event.target.value)} placeholder="e.g. CS student interested in AI engineering" /></label>{inputFields.map((field) => <label className="field-label field-full" key={field.key}>{field.label}<input value={Array.isArray(form[field.key]) ? form[field.key].join(', ') : form[field.key] || ''} onChange={(event) => updateForm(field.key, event.target.value)} placeholder={field.placeholder} /><span className="field-help">{field.help}</span></label>)}<label className="field-label">Minimum monthly salary (₹)<input type="number" min="0" value={form.min_salary ?? ''} onChange={(event) => updateForm('min_salary', event.target.value)} placeholder="30000" /><span className="field-help">Leave blank if flexible.</span></label><label className="field-label field-full">Additional context<textarea rows={3} value={form.notes || ''} onChange={(event) => updateForm('notes', event.target.value)} placeholder="Industries, learning goals, company stage, or other preferences…" /></label></div><div className="form-footer"><span><ShieldCheck size={15} /> Stored in your configured database</span><button className="button button-primary" type="submit" disabled={saving}>{saving ? <LoaderCircle className="spin" size={16} /> : <Check size={16} />}{saving ? 'Saving…' : 'Save preferences'}</button></div></form><aside className="profile-side-column"><div className="side-panel profile-insight"><div className="eyebrow">WHY IT MATTERS</div><h3>Better input.<br /><span>More relevant matches.</span></h3><p>Your preferences are used by a transparent baseline scorer. You can inspect the reasons and missing skills on every role.</p><div className="insight-stat"><div><strong>{stats.skills_count}</strong><span>skills tracked</span></div><div><strong>{stats.total_jobs}</strong><span>sample jobs</span></div></div></div><div className="side-panel skill-preview"><div className="panel-heading"><h3>Skills in your profile</h3><span>{(Array.isArray(form.skills) ? form.skills : splitList(form.skills || '')).length}</span></div><div className="profile-skill-cloud">{(Array.isArray(form.skills) ? form.skills : splitList(form.skills || '')).map((skill) => <span className="profile-skill" key={skill}>{skill}</span>)}</div>{!(Array.isArray(form.skills) ? form.skills : splitList(form.skills || '')).length && <p className="muted-small">Add a few skills to see them here.</p>}</div><div className="profile-privacy-note"><ShieldCheck size={17} /><div><strong>You're in control</strong><span>This sample app uses one local demo profile. Do not add sensitive personal data.</span></div></div></aside></div></div>;
}

function EmptyState({ icon: Icon, title, body, action, onAction }) {
  return <div className="empty-state"><div className="empty-icon"><Icon size={22} /></div><h3>{title}</h3><p>{body}</p>{action && <button className="button button-primary" onClick={onAction}>{action}<ArrowRight size={15} /></button>}</div>;
}

function JobModal({ job, saved, onClose, onSave }) {
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}><section className="job-modal" role="dialog" aria-modal="true" aria-labelledby="job-modal-title"><div className="modal-topline"><span className="eyebrow">SAMPLE LISTING · #{job.id}</span><button className="icon-button" onClick={onClose} aria-label="Close job details"><X size={18} /></button></div><div className="modal-company-row"><div className={`company-monogram monogram-${job.id % 5}`}>{initials(job.company)}</div><div><h2 id="job-modal-title">{job.title}</h2><p>{job.company}</p></div><div className="modal-score"><strong>{job.match_score}%</strong><span>match</span></div></div><div className="job-meta modal-meta"><span><MapPin size={14} />{job.location}</span><span><Clock3 size={14} />{job.job_type}</span><span className="work-mode-tag">{job.work_mode}</span></div><div className="modal-salary">{job.salary}<span>{job.experience}</span></div><p className="modal-description">{job.description}</p><div className="modal-section"><h3>Required skills</h3><div className="skills-row">{job.required_skills.map((skill) => <span className="skill-chip" key={skill}>{skill}</span>)}</div></div>{job.nice_to_have?.length > 0 && <div className="modal-section"><h3>Nice to have</h3><div className="skills-row">{job.nice_to_have.map((skill) => <span className="skill-chip skill-chip-muted" key={skill}>{skill}</span>)}</div></div>}<div className="modal-section"><h3>What you might work on</h3><ul className="responsibility-list">{job.responsibilities.map((item) => <li key={item}><Check size={15} />{item}</li>)}</ul></div><div className="modal-match-explain"><div className="modal-match-head"><Target size={17} /><strong>Why this could fit</strong></div><ul>{(job.match_reasons || []).map((reason) => <li key={reason}>{reason}</li>)}</ul>{job.missing_skills?.length > 0 && <div className="missing-skills"><strong>Skills to explore:</strong> {job.missing_skills.join(', ')}</div>}<p>Match scores are simple heuristics for this demo and are not a probability of being hired. Listings are synthetic and not verified live vacancies.</p></div><div className="modal-actions"><button className={`button ${saved ? 'button-outline' : 'button-primary'}`} onClick={onSave}>{saved ? <Check size={16} /> : <Bookmark size={16} />}{saved ? 'Saved to shortlist' : 'Save this job'}</button><button className="button button-ghost" onClick={onClose}>Close</button></div></section></div>;
}

export default App;
