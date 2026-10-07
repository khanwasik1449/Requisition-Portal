import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/api/axios'
import { PageStyle } from '@/components/PageStyle'
import { flashFromError, setFlash, takeFlash, type FlashLevel } from '@/lib/flash'

interface EmailConfig {
  id?: number
  email_host: string
  email_port: number
  email_use_tls: boolean
  email_host_user: string
  email_host_password: string
  default_from_email: string
}

interface ConfigResult {
  detail: string
  level: FlashLevel
  config: EmailConfig
}

interface FormState {
  email_host: string
  email_port: string
  email_use_tls: boolean
  email_host_user: string
  email_host_password: string
  default_from_email: string
}

function toForm(config: EmailConfig): FormState {
  return {
    email_host: config.email_host ?? '',
    email_port: String(config.email_port ?? 587),
    email_use_tls: Boolean(config.email_use_tls),
    email_host_user: config.email_host_user ?? '',
    email_host_password: config.email_host_password ?? '',
    default_from_email: config.default_from_email ?? '',
  }
}

// contracts/templates/contracts/email_settings.html -- <style> block, verbatim.
const css = `
  .es-wrap { max-width: 600px; margin: 0 auto; }
  .es-card { background: #fff; border: 1px solid #E2E8F0; border-radius: 16px; padding: 28px; }
  .es-card h2 { margin: 0 0 4px; }
  .es-sub { color: #64748B; font-size: 13px; margin-bottom: 24px; }
  .es-field { margin-bottom: 20px; }
  .es-field label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: #334155; }
  .es-field input[type="text"],
  .es-field input[type="email"],
  .es-field input[type="password"],
  .es-field input[type="number"] {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #E2E8F0;
    border-radius: 10px;
    font-size: 14px;
    outline: none;
    transition: border-color .15s;
  }
  .es-field input:focus { border-color: #2563EB; box-shadow: 0 0 0 3px rgba(37,99,235,.08); }
  .es-toggle { display: flex; align-items: center; gap: 10px; margin-top: 8px; }
  .es-toggle input[type="checkbox"] { width: 18px; height: 18px; accent-color: #2563EB; }
  .es-actions { display: flex; gap: 12px; margin-top: 8px; }
  .es-save {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 24px; background: #2563EB; color: #fff;
    border: none; border-radius: 10px; font-size: 14px; font-weight: 600; cursor: pointer;
  }
  .es-save:hover { background: #1D4ED8; }
  .es-test {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 10px 20px; background: #fff; color: #2563EB;
    border: 1px solid #2563EB; border-radius: 10px; font-size: 14px; font-weight: 500; cursor: pointer;
  }
  .es-test:hover { background: #EFF6FF; }
  .es-note {
    margin-top: 20px; padding: 12px 16px;
    background: #FFF7ED; border-left: 4px solid #F97316;
    border-radius: 8px; font-size: 13px; color: #9A3412;
  }
  .es-tip {
    margin-top: 12px; padding: 12px 16px;
    background: #EFF6FF; border-left: 4px solid #2563EB;
    border-radius: 8px; font-size: 13px; color: #1E40AF;
  }
`

// Replica of contracts/templates/contracts/email_settings.html
export function HrEmailSettings() {
  const queryClient = useQueryClient()

  const [form, setForm] = useState<FormState>(toForm({} as EmailConfig))
  const [loaded, setLoaded] = useState(false)
  const [notice, setNotice] = useState<{ level: FlashLevel; text: string } | null>(null)
  const ownsFlash = useRef(false)

  // Neither branch of email_settings leaves the page -- main re-renders it
  // with the messages block on save and without one on test -- so the
  // sentence is shown inline and the shared slot dropped again on unmount.
  useEffect(() => {
    return () => {
      if (ownsFlash.current) takeFlash()
    }
  }, [])

  const configQuery = useQuery({
    queryKey: ['contracts', 'email-config'],
    queryFn: async () => (await api.get<EmailConfig>('/contracts/email-config/')).data,
  })

  // Seed the six inputs once, then let the local draft take over: the test
  // branch reports an edited config back without saving it.
  useEffect(() => {
    if (configQuery.data && !loaded) {
      setForm(toForm(configQuery.data))
      setLoaded(true)
    }
  }, [configQuery.data, loaded])

  useEffect(() => {
    if (configQuery.isError) {
      const text = flashFromError(configQuery.error).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
    }
  }, [configQuery.isError, configQuery.error])

  function setField<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  const submit = useMutation({
    mutationFn: async (action: 'save' | 'test') => {
      const response = await api.post<ConfigResult>('/contracts/email-config/', {
        ...form,
        action,
      })
      return response.data
    },
    onSuccess: (data, action) => {
      const level: FlashLevel = data.level === 'success' ? 'success' : 'error'
      // Django queues this sentence and re-renders the page from the redirect;
      // staying put means the message is drawn inline as well as flashed.
      setFlash(level, data.detail)
      ownsFlash.current = true
      setNotice({ level, text: data.detail })
      if (data.config) setForm(toForm(data.config))
      if (action === 'save') queryClient.invalidateQueries({ queryKey: ['contracts'] })
    },
    onError: (err: unknown) => {
      const text = flashFromError(err).text
      setFlash('error', text)
      ownsFlash.current = true
      setNotice({ level: 'error', text })
      // A failed test still hands back the config it tried in memory.
      const config = (err as { response?: { data?: { config?: EmailConfig } } } | null)?.response
        ?.data?.config
      if (config) setForm(toForm(config))
    },
  })

  return (
    <>
      <PageStyle css={css} />

      <div className="es-wrap">
        <div className="es-card">
          <h2>⚙️ Email Settings</h2>
          <p className="es-sub">
            Configure SMTP server for sending contract emails. Changes apply immediately.
          </p>

          {notice && (
            <div className={`app-message ${notice.level}`}>
              <span className="msg-close" onClick={() => setNotice(null)}>
                &times;
              </span>
              {notice.text}
            </div>
          )}

          <form
            onSubmit={(e) => {
              e.preventDefault()
              submit.mutate('save')
            }}
          >
            <div className="es-field">
              <label>SMTP Host</label>
              <input
                type="text"
                name="email_host"
                required
                placeholder="smtp.gmail.com"
                value={form.email_host}
                onChange={(e) => setField('email_host', e.target.value)}
              />
            </div>

            <div className="es-field">
              <label>SMTP Port</label>
              <input
                type="number"
                name="email_port"
                required
                placeholder="587"
                value={form.email_port}
                onChange={(e) => setField('email_port', e.target.value)}
              />
            </div>

            <div className="es-field">
              <label>Use TLS</label>
              <div className="es-toggle">
                <input
                  type="checkbox"
                  name="email_use_tls"
                  checked={form.email_use_tls}
                  onChange={(e) => setField('email_use_tls', e.target.checked)}
                />
                <span style={{ fontSize: '13px', color: '#64748B' }}>
                  Enable TLS encryption (recommended)
                </span>
              </div>
            </div>

            <div className="es-field">
              <label>Email Address</label>
              <input
                type="email"
                name="email_host_user"
                required
                placeholder="you@example.com"
                value={form.email_host_user}
                onChange={(e) => setField('email_host_user', e.target.value)}
              />
            </div>

            <div className="es-field">
              <label>Email Password / App Password</label>
              <input
                type="password"
                name="email_host_password"
                required
                placeholder="••••••••"
                value={form.email_host_password}
                onChange={(e) => setField('email_host_password', e.target.value)}
              />
            </div>

            <div className="es-field">
              <label>Display Name (From)</label>
              <input
                type="text"
                name="default_from_email"
                required
                value={form.default_from_email}
                onChange={(e) => setField('default_from_email', e.target.value)}
              />
            </div>

            <div className="es-actions">
              <button
                type="submit"
                className="es-save"
                disabled={submit.isPending && submit.variables === 'save'}
              >
                💾 Save Settings
              </button>
              <button
                type="button"
                className="es-test"
                disabled={submit.isPending && submit.variables === 'test'}
                onClick={() => submit.mutate('test')}
              >
                🔗 Test Connection
              </button>
            </div>

            <div className="es-tip">
              <strong>💡 Tip:</strong> Click <strong>Test Connection</strong> to verify the SMTP
              server before saving.
            </div>

            <div className="es-note">
              <strong>⚠️ Gmail:</strong> Use an <em>App Password</em> instead of your regular
              password. Generate one at{' '}
              <a
                href="https://myaccount.google.com/apppasswords"
                target="_blank"
                rel="noopener"
                style={{ color: '#9A3412' }}
              >
                Google App Passwords
              </a>
            </div>
          </form>
        </div>
      </div>
    </>
  )
}
