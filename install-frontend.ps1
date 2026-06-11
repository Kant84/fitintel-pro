# FitIntel Pro - Frontend Installer
# Run from project root: .\install-frontend.ps1

$ErrorActionPreference = "Stop"
$projectRoot = "C:\Users\PC\Desktop\2026\FitNexus AI\FitNexus AI"
$frontendDir = Join-Path $projectRoot "frontend"

Write-Host "=== FitIntel Pro Frontend Installer ===" -ForegroundColor Green

# Step 1: Clean old frontend
if (Test-Path $frontendDir) {
    Write-Host "Removing old frontend..." -ForegroundColor Yellow
    Remove-Item -Recurse -Force $frontendDir
}

# Step 2: Create Vite project
Write-Host "Creating Vite + React + TypeScript project..." -ForegroundColor Cyan
Set-Location $projectRoot
$npxCmd = "create vite@latest frontend -- --template react-ts"
Start-Process -FilePath "npx" -ArgumentList $npxCmd -Wait -NoNewWindow

# Step 3: Install dependencies
Write-Host "Installing dependencies..." -ForegroundColor Cyan
Set-Location $frontendDir
npm install
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

npm install react-router-dom axios zustand
npm install @radix-ui/react-slot @radix-ui/react-dialog @radix-ui/react-label @radix-ui/react-select @radix-ui/react-tabs @radix-ui/react-separator @radix-ui/react-scroll-area @radix-ui/react-avatar @radix-ui/react-badge @radix-ui/react-dropdown-menu @radix-ui/react-popover @radix-ui/react-toast class-variance-authority clsx tailwind-merge lucide-react

# Step 4: Configure Tailwind
Write-Host "Configuring Tailwind..." -ForegroundColor Cyan
$tailwindConfig = @"/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        secondary: { DEFAULT: 'hsl(var(--secondary))', foreground: 'hsl(var(--secondary-foreground))' },
        destructive: { DEFAULT: 'hsl(var(--destructive))', foreground: 'hsl(var(--destructive-foreground))' },
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        popover: { DEFAULT: 'hsl(var(--popover))', foreground: 'hsl(var(--popover-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [],
}
"@
Set-Content -Path "tailwind.config.js" -Value $tailwindConfig -Encoding UTF8

# Step 5: Configure CSS
$cssContent = @"@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 160 84% 39%;
    --primary-foreground: 0 0% 100%;
    --secondary: 210 40% 96.1%;
    --secondary-foreground: 222.2 47.4% 11.2%;
    --muted: 210 40% 96.1%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96.1%;
    --accent-foreground: 222.2 47.4% 11.2%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 160 84% 39%;
    --radius: 0.5rem;
  }
}

@layer base {
  * { @apply border-border; }
  body { @apply bg-background text-foreground; }
}
"@
Set-Content -Path "src/index.css" -Value $cssContent -Encoding UTF8

# Step 6: Create utils
New-Item -ItemType Directory -Force -Path "src/lib"
$utilsContent = @"import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
"@
Set-Content -Path "src/lib/utils.ts" -Value $utilsContent -Encoding UTF8

# Step 7: Create all page files
Write-Host "Creating page files..." -ForegroundColor Cyan

# Create directories
$dirs = @('src/store', 'src/layouts', 'src/pages/admin', 'src/pages/client', 'src/pages/auth', 'src/components/ui')
foreach ($d in $dirs) { New-Item -ItemType Directory -Force -Path $d | Out-Null }

# UI Components (minimal set)
$components = @{
    'button' = @"import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
const buttonVariants = cva('inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50', {
  variants: {
    variant: {
      default: 'bg-emerald-600 text-white hover:bg-emerald-700',
      destructive: 'bg-red-600 text-white hover:bg-red-700',
      outline: 'border border-input bg-background hover:bg-accent hover:text-accent-foreground',
      secondary: 'bg-slate-100 text-slate-800 hover:bg-slate-200',
      ghost: 'hover:bg-accent hover:text-accent-foreground',
      link: 'text-emerald-600 underline-offset-4 hover:underline',
    },
    size: {
      default: 'h-10 px-4 py-2',
      sm: 'h-8 px-3',
      lg: 'h-11 px-8',
      icon: 'h-10 w-10',
    },
  },
  defaultVariants: { variant: 'default', size: 'default' },
})
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(({ className, variant, size, ...props }, ref) => {
  return <button className={cn(buttonVariants({ variant, size, className }))} ref={ref} {...props} />
})
Button.displayName = 'Button'
export { Button, buttonVariants }
"@
    'card' = @"import * as React from 'react'
import { cn } from '@/lib/utils'
const Card = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) =>
  <div ref={ref} className={cn('rounded-lg border bg-card text-card-foreground shadow-sm', className)} {...props} />)
Card.displayName = 'Card'
const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) =>
  <div ref={ref} className={cn('flex flex-col space-y-1.5 p-6', className)} {...props} />)
CardHeader.displayName = 'CardHeader'
const CardTitle = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className, ...props }, ref) =>
  <h3 ref={ref} className={cn('text-2xl font-semibold leading-none tracking-tight', className)} {...props} />)
CardTitle.displayName = 'CardTitle'
const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) =>
  <div ref={ref} className={cn('p-6 pt-0', className)} {...props} />)
CardContent.displayName = 'CardContent'
export { Card, CardHeader, CardTitle, CardContent }
"@
    'input' = @"import * as React from 'react'
import { cn } from '@/lib/utils'
export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}
const Input = React.forwardRef<HTMLInputElement, InputProps>(({ className, type, ...props }, ref) => {
  return <input type={type} className={cn('flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50', className)} ref={ref} {...props} />
})
Input.displayName = 'Input'
export { Input }
"@
    'label' = @"import * as React from 'react'
import { cn } from '@/lib/utils'
const Label = React.forwardRef<HTMLLabelElement, React.LabelHTMLAttributes<HTMLLabelElement>>(({ className, ...props }, ref) =>
  <label ref={ref} className={cn('text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70', className)} {...props} />)
Label.displayName = 'Label'
export { Label }
"@
    'badge' = @"import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
const badgeVariants = cva('inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2', {
  variants: {
    variant: {
      default: 'border-transparent bg-emerald-600 text-white hover:bg-emerald-700',
      secondary: 'border-transparent bg-slate-100 text-slate-800 hover:bg-slate-200',
      destructive: 'border-transparent bg-red-600 text-white hover:bg-red-700',
      outline: 'text-slate-800',
    },
  },
  defaultVariants: { variant: 'default' },
})
export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}
function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}
export { Badge, badgeVariants }
"@
    'separator' = @"import * as React from 'react'
import { cn } from '@/lib/utils'
const Separator = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) =>
  <div ref={ref} className={cn('shrink-0 bg-border h-[1px] w-full', className)} {...props} />)
Separator.displayName = 'Separator'
export { Separator }
"@
    'skeleton' = @"import { cn } from '@/lib/utils'
function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('animate-pulse rounded-md bg-slate-200', className)} {...props} />
}
export { Skeleton }
"@
    'scroll-area' = @"import * as React from 'react'
import { cn } from '@/lib/utils'
const ScrollArea = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, children, ...props }, ref) => (
  <div ref={ref} className={cn('relative overflow-auto', className)} {...props}>{children}</div>
))
ScrollArea.displayName = 'ScrollArea'
export { ScrollArea }
"@
    'alert' = @"import * as React from 'react'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'
const alertVariants = cva('relative w-full rounded-lg border p-4', {
  variants: {
    variant: {
      default: 'bg-white text-slate-800',
      destructive: 'border-red-200 bg-red-50 text-red-800',
    },
  },
  defaultVariants: { variant: 'default' },
})
const Alert = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & VariantProps<typeof alertVariants>>(({ className, variant, ...props }, ref) =>
  <div ref={ref} role='alert' className={cn(alertVariants({ variant }), className)} {...props} />)
Alert.displayName = 'Alert'
const AlertDescription = React.forwardRef<HTMLParagraphElement, React.HTMLAttributes<HTMLParagraphElement>>(({ className, ...props }, ref) =>
  <div ref={ref} className={cn('text-sm', className)} {...props} />)
AlertDescription.displayName = 'AlertDescription'
export { Alert, AlertDescription }
"@
    'tabs' = @"import * as React from 'react'
import { cn } from '@/lib/utils'
const Tabs = ({ defaultValue, children, className }: { defaultValue: string; children: React.ReactNode; className?: string }) => {
  const [value, setValue] = React.useState(defaultValue)
  return <div className={cn('w-full', className)} data-tabs-value={value}>{React.Children.map(children, child => React.isValidElement(child) ? React.cloneElement(child as React.ReactElement<any>, { _tabsValue: value, _setValue: setValue }) : child)}</div>
}
const TabsList = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { _tabsValue?: string; _setValue?: (v: string) => void }>(({ className, ...props }, ref) =>
  <div ref={ref} className={cn('inline-flex h-10 items-center justify-center rounded-md bg-slate-100 p-1 text-slate-600', className)} {...props} />)
TabsList.displayName = 'TabsList'
const TabsTrigger = React.forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string; _tabsValue?: string; _setValue?: (v: string) => void }>(({ className, value, _tabsValue, _setValue, onClick, ...props }, ref) =>
  <button ref={ref} onClick={(e) => { _setValue?.(value); onClick?.(e as any) }} className={cn('inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5 text-sm font-medium ring-offset-background transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50', _tabsValue === value ? 'bg-white text-slate-900 shadow-sm' : 'hover:bg-white/50 hover:text-slate-800', className)} {...props} />)
TabsTrigger.displayName = 'TabsTrigger'
const TabsContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement> & { value: string; _tabsValue?: string }>(({ className, value, _tabsValue, ...props }, ref) => {
  if (_tabsValue !== value) return null
  return <div ref={ref} className={cn('mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2', className)} {...props} />
})
TabsContent.displayName = 'TabsContent'
export { Tabs, TabsList, TabsTrigger, TabsContent }
"@
    'dialog' = @"import * as React from 'react'
import { cn } from '@/lib/utils'
const Dialog = ({ open, onOpenChange, children }: { open: boolean; onOpenChange: (v: boolean) => void; children: React.ReactNode }) => {
  if (!open) return null
  return <div className='fixed inset-0 z-50 flex items-center justify-center' onClick={() => onOpenChange(false)}>
    <div className='fixed inset-0 bg-black/50' />
    <div onClick={e => e.stopPropagation()}>{children}</div>
  </div>
}
const DialogContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(({ className, ...props }, ref) =>
  <div ref={ref} className={cn('relative z-50 grid w-full max-w-lg gap-4 border bg-white p-6 shadow-lg rounded-lg', className)} {...props} />)
DialogContent.displayName = 'DialogContent'
const DialogHeader = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) =>
  <div className={cn('flex flex-col space-y-1.5 text-center sm:text-left', className)} {...props} />
const DialogTitle = React.forwardRef<HTMLHeadingElement, React.HTMLAttributes<HTMLHeadingElement>>(({ className, ...props }, ref) =>
  <h3 ref={ref} className={cn('text-lg font-semibold leading-none tracking-tight', className)} {...props} />)
DialogTitle.displayName = 'DialogTitle'
export { Dialog, DialogContent, DialogHeader, DialogTitle }
"@
}

foreach ($comp in $components.Keys) {
    Set-Content -Path "src/components/ui/$comp.tsx" -Value $components[$comp] -Encoding UTF8
}

# Step 8: Create API files
Write-Host "Creating API files..." -ForegroundColor Cyan

$apiMockContent = @"export const USE_MOCK = true;

const delay = (ms: number) => new Promise(r => setTimeout(r, ms));

export const mockAuthApi = {
  login: async (login: string, password: string) => {
    await delay(500);
    if (login === 'admin' && password === 'admin') {
      return { data: { access_token: 'mock_token', token_type: 'bearer', expires_in: 1800 } };
    }
    throw { response: { data: { detail: 'Неверный логин или пароль' } } };
  },
  me: async () => ({
    data: {
      id: '550e8400-e29b-41d4-a716-446655440000',
      email: 'admin@fitintel.pro',
      username: 'admin',
      is_active: true,
      roles: ['owner', 'admin'],
      permissions: ['users.read', 'users.create', 'clients.read', 'clients.create', 'subscriptions.read', 'visits.read', 'payments.read', 'analytics.read', 'devices.read'],
    }
  }),
  tokenCheck: async () => ({ data: { message: 'OK' } }),
};

export const mockClientsApi = {
  list: async () => ({
    data: {
      items: [
        { id: '1', first_name: 'Алексей', last_name: 'Иванов', phone: '+79991234567', email: 'alex@mail.ru', status: 'ACTIVE', is_active: true },
        { id: '2', first_name: 'Мария', last_name: 'Петрова', phone: '+79992345678', email: 'maria@mail.ru', status: 'ACTIVE', is_active: true },
        { id: '3', first_name: 'Дмитрий', last_name: 'Сидоров', phone: '+79993456789', email: 'dima@mail.ru', status: 'BLOCKED', is_active: false },
        { id: '4', first_name: 'Елена', last_name: 'Кузнецова', phone: '+79994567890', email: 'elena@mail.ru', status: 'FROZEN', is_active: true },
      ], count: 4
    }
  }),
  get: async (id: string) => ({ data: { id, first_name: 'Тест', last_name: 'Клиент', phone: '+79999999999', status: 'ACTIVE' } }),
  create: async (data: any) => ({ data: { id: Math.random().toString(36), ...data } }),
  update: async (id: string, data: any) => ({ data: { id, ...data } }),
};

export const mockSubscriptionsApi = {
  list: async () => ({
    data: {
      items: [
        { id: 's1', tariff_name: 'Базовый (1 мес)', client_name: 'Алексей И.', client_id: '1', status: 'ACTIVE', start_date: '2026-05-01', end_date: '2026-06-01', visits_left: 8, freeze_until: null },
        { id: 's2', tariff_name: 'VIP (3 мес)', client_name: 'Мария П.', client_id: '2', status: 'ACTIVE', start_date: '2026-04-15', end_date: '2026-07-15', visits_left: 25, freeze_until: null },
        { id: 's3', tariff_name: 'Базовый (1 мес)', client_name: 'Елена К.', client_id: '4', status: 'FROZEN', start_date: '2026-04-01', end_date: '2026-05-01', visits_left: 5, freeze_until: '2026-06-15' },
      ], count: 3
    }
  }),
  freeze: async () => ({ data: { status: 'FROZEN' } }),
  unfreeze: async () => ({ data: { status: 'ACTIVE' } }),
  renew: async () => ({ data: { status: 'ACTIVE' } }),
  cancel: async () => ({ data: { status: 'CANCELLED' } }),
};

export const mockVisitsApi = {
  entry: async () => ({ data: { id: 'v1', status: 'ACTIVE' } }),
  exit: async () => ({ data: { id: 'v1', status: 'COMPLETED' } }),
  active: async () => ({
    data: {
      items: [
        { id: 'v1', client_name: 'Алексей И.', client_id: '1', entry_time: '2026-06-11T08:30:00', exit_time: null, status: 'ACTIVE' },
        { id: 'v2', client_name: 'Мария П.', client_id: '2', entry_time: '2026-06-11T09:15:00', exit_time: null, status: 'ACTIVE' },
      ]
    }
  }),
  statsToday: async () => ({ data: { entries: 23, exits: 18, avg_duration: 67 } }),
};

export const mockFinanceApi = {
  walletMe: async () => ({ data: { id: 'w1', client_id: '1', balance: 1500, currency: 'RUB', frozen_balance: 0 } }),
  walletTransactions: async () => ({
    data: {
      items: [
        { id: 't1', type: 'DEPOSIT', amount: 2000, currency: 'RUB', description: 'Пополнение', created_at: '2026-06-10T14:00:00' },
        { id: 't2', type: 'PAYMENT', amount: -500, currency: 'RUB', description: 'Абонемент Базовый', created_at: '2026-06-09' },
      ]
    }
  }),
  payments: async () => ({
    data: {
      items: [
        { id: 'p1', amount: 500, currency: 'RUB', status: 'COMPLETED', description: 'Базовый', client_name: 'Алексей И.' },
        { id: 'p2', amount: 1500, currency: 'RUB', status: 'COMPLETED', description: 'VIP', client_name: 'Мария П.' },
        { id: 'p3', amount: 300, currency: 'RUB', status: 'PENDING', description: 'Разовое', client_name: 'Сергей С.' },
      ]
    }
  }),
  cashDeskCurrent: async () => ({ data: { session_id: 'c1', status: 'OPEN' } }),
};

export const mockAccessApi = {
  check: async () => ({ data: { allowed: true, client_name: 'Алексей И.', message: 'Доступ разрешен' } }),
  grant: async () => ({ data: { granted: true } }),
  credentials: async () => ({ data: { items: [] } }),
  qrGet: async () => ({ data: { qr_data: 'mock-qr' } }),
  lockers: async () => ({ data: { items: [] } }),
};

export const mockAnalyticsApi = {
  dashboard: async () => ({
    data: {
      period: '2026-06-01 - 2026-06-11',
      clients: { total: 247, active: 189 },
      visits_today: 23,
      subscriptions_active: 156,
      revenue_month: 345000,
    }
  }),
  visits: async () => ({
    data: {
      daily: [
        { day: '2026-06-05', visits: 18, unique_clients: 15 },
        { day: '2026-06-06', visits: 22, unique_clients: 18 },
        { day: '2026-06-07', visits: 25, unique_clients: 20 },
        { day: '2026-06-08', visits: 20, unique_clients: 16 },
        { day: '2026-06-09', visits: 28, unique_clients: 22 },
        { day: '2026-06-10', visits: 30, unique_clients: 24 },
        { day: '2026-06-11', visits: 23, unique_clients: 19 },
      ],
      total_visits: 186,
    }
  }),
};

export const mockDevicesApi = {
  list: async () => ({
    data: {
      items: [
        { id: 'd1', name: 'Турникет Главный', device_type: 'turnstile', location: 'Вход', is_active: true, last_ping: new Date().toISOString() },
        { id: 'd2', name: 'Турникет Задний', device_type: 'turnstile', location: 'Задний вход', is_active: true, last_ping: new Date(Date.now()-60000).toISOString() },
        { id: 'd3', name: 'Шкафчик-контроллер', device_type: 'locker_controller', location: 'Раздевалка', is_active: true, last_ping: new Date(Date.now()-120000).toISOString() },
        { id: 'd4', name: 'Считыватель RFID', device_type: 'rfid_reader', location: 'Рецепция', is_active: false, last_ping: new Date(Date.now()-600000).toISOString() },
      ]
    }
  }),
  ping: async () => ({ data: { status: 'ok' } }),
};

export const mockSelfserviceApi = {
  profile: async () => ({
    data: {
      user: { id: '1', email: 'alex@mail.ru', username: 'alexey', roles: ['client'] },
      client: { id: '1', first_name: 'Алексей', last_name: 'Иванов', phone: '+79991234567', status: 'ACTIVE', created_at: '2026-01-15' },
      wallet: { balance: 1500, currency: 'RUB' },
    }
  }),
  subscriptions: async () => ({
    data: {
      items: [
        { id: 's1', tariff_name: 'Базовый (1 мес)', status: 'ACTIVE', start_date: '2026-05-01', end_date: '2026-06-01', visits_left: 8, freeze_until: null },
      ]
    }
  }),
  visits: async () => ({
    data: {
      items: [
        { id: 'v1', entry_time: '2026-06-11T08:30:00', exit_time: '2026-06-11T09:45:00', duration_minutes: 75, status: 'COMPLETED' },
        { id: 'v2', entry_time: '2026-06-10T18:00:00', exit_time: '2026-06-10T19:30:00', duration_minutes: 90, status: 'COMPLETED' },
      ]
    }
  }),
};
"@
Set-Content -Path "src/lib/api-mock.ts" -Value $apiMockContent -Encoding UTF8

$apiContent = @"import axios from 'axios';
import {
  USE_MOCK,
  mockAuthApi, mockClientsApi, mockSubscriptionsApi, mockVisitsApi,
  mockFinanceApi, mockAccessApi, mockAnalyticsApi, mockSelfserviceApi, mockDevicesApi,
} from './api-mock';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
export const api = axios.create({ baseURL: API_BASE, headers: { 'Content-Type': 'application/json' } });
api.interceptors.request.use((config) => { const token = localStorage.getItem('access_token'); if (token) config.headers.Authorization = `Bearer ${token}`; return config; });
api.interceptors.response.use((r) => r, (e) => { if (e.response?.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; } return Promise.reject(e); });

export const authApi = USE_MOCK ? mockAuthApi : { login: (l: string, p: string) => api.post('/auth/login', { login: l, password: p }), me: () => api.get('/auth/me'), tokenCheck: () => api.get('/auth/token-check') };
export const clientsApi = USE_MOCK ? mockClientsApi : { list: (p?: any) => api.get('/clients/', { params: p }), get: (id: string) => api.get(`/clients/${id}`), create: (d: any) => api.post('/clients/', d), update: (id: string, d: any) => api.patch(`/clients/${id}`, d) };
export const subscriptionsApi = USE_MOCK ? mockSubscriptionsApi : { list: (p?: any) => api.get('/subscriptions/', { params: p }), freeze: (id: string) => api.post(`/subscriptions/${id}/freeze`), unfreeze: (id: string) => api.post(`/subscriptions/${id}/unfreeze`), renew: (id: string) => api.post(`/subscriptions/${id}/renew`), cancel: (id: string) => api.post(`/subscriptions/${id}/cancel`) };
export const visitsApi = USE_MOCK ? mockVisitsApi : { entry: (d: any) => api.post('/visits/entry', d), exit: (d: any) => api.post('/visits/exit', d), active: () => api.get('/visits/active'), statsToday: () => api.get('/visits/stats/today') };
export const financeApi = USE_MOCK ? mockFinanceApi : { walletMe: () => api.get('/wallet/me'), walletTransactions: () => api.get('/wallet/me/transactions'), payments: (p?: any) => api.get('/payments/', { params: p }), cashDeskCurrent: () => api.get('/cash-desk/current') };
export const accessApi = USE_MOCK ? mockAccessApi : { check: (d: any) => api.post('/access/check', d), grant: (d: any) => api.post('/access/grant', d), credentials: (id: string) => api.get(`/credentials/client/${id}`), qrGet: (id: string) => api.get(`/credentials/qr/client/${id}`), lockers: () => api.get('/lockers/') };
export const analyticsApi = USE_MOCK ? mockAnalyticsApi : { dashboard: () => api.get('/analytics/dashboard'), visits: (s: string, e: string) => api.get('/analytics/visits', { params: { start: s, end: e } }) };
export const selfserviceApi = USE_MOCK ? mockSelfserviceApi : { profile: () => api.get('/selfservice/profile'), subscriptions: () => api.get('/selfservice/subscriptions'), visits: () => api.get('/selfservice/visits') };
export const devicesApi = USE_MOCK ? mockDevicesApi : { list: () => api.get('/devices/'), ping: (id: string) => api.post(`/devices/${id}/ping`) };
export const rbacApi = { roles: () => api.get('/roles/'), permissions: () => api.get('/permissions/') };
"@
Set-Content -Path "src/lib/api.ts" -Value $apiContent -Encoding UTF8

# Step 9: Auth store
Write-Host "Creating auth store..." -ForegroundColor Cyan
$storeContent = @"import { create } from 'zustand';
import { authApi } from '@/lib/api';

interface User { id: string; email: string | null; username: string | null; is_active: boolean; roles: string[]; permissions: string[]; }
interface AuthState { token: string | null; user: User | null; isAuthenticated: boolean; isLoading: boolean; login: (l: string, p: string) => Promise<void>; logout: () => void; fetchMe: () => Promise<void>; hasPermission: (p: string) => boolean; hasRole: (r: string) => boolean; }

export const useAuthStore = create<AuthState>((set, get) => ({
  token: localStorage.getItem('access_token'), user: null, isAuthenticated: !!localStorage.getItem('access_token'), isLoading: false,
  login: async (login, password) => {
    set({ isLoading: true });
    try { const res = await authApi.login(login, password); const { access_token } = res.data; localStorage.setItem('access_token', access_token); set({ token: access_token, isAuthenticated: true }); await get().fetchMe(); } finally { set({ isLoading: false }); }
  },
  logout: () => { localStorage.removeItem('access_token'); set({ token: null, user: null, isAuthenticated: false }); },
  fetchMe: async () => { try { const res = await authApi.me(); set({ user: res.data }); } catch { get().logout(); } },
  hasPermission: (perm) => { const u = get().user; return !!u && (u.permissions.includes(perm) || u.roles.includes('owner') || u.roles.includes('admin')); },
  hasRole: (role) => { const u = get().user; return !!u && u.roles.includes(role); },
}));
"@
Set-Content -Path "src/store/authStore.ts" -Value $storeContent -Encoding UTF8

# Step 10: Layouts
Write-Host "Creating layouts and pages..." -ForegroundColor Cyan

$adminLayout = @"import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { LayoutDashboard, Users, CreditCard, DoorOpen, Wallet, Settings, LogOut, Dumbbell, Bell, QrCode, BarChart3 } from 'lucide-react';

const navItems = [
  { path: '/', label: 'Дашборд', icon: LayoutDashboard },
  { path: '/clients', label: 'Клиенты', icon: Users },
  { path: '/subscriptions', label: 'Абонементы', icon: CreditCard },
  { path: '/visits', label: 'Посещения', icon: DoorOpen },
  { path: '/access', label: 'Доступ', icon: QrCode },
  { path: '/finance', label: 'Финансы', icon: Wallet },
  { path: '/devices', label: 'Устройства', icon: Dumbbell },
  { path: '/analytics', label: 'Аналитика', icon: BarChart3 },
  { path: '/settings', label: 'Настройки', icon: Settings },
];

export default function AdminLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const handleLogout = () => { logout(); navigate('/login'); };
  return (
    <div className="flex h-screen bg-slate-50">
      <aside className="w-64 bg-slate-900 text-white flex flex-col">
        <div className="p-4 flex items-center gap-3">
          <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center"><Dumbbell className="w-5 h-5" /></div>
          <span className="font-bold text-lg">FitIntel Pro</span>
        </div>
        <Separator className="bg-slate-700" />
        <ScrollArea className="flex-1 py-2">
          <nav className="px-2 space-y-1">
            {navItems.map(item => {
              const Icon = item.icon;
              const active = location.pathname === item.path;
              return <Link key={item.path} to={item.path} className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors 
${active ? 'bg-emerald-600 text-white' : 'text-slate-300 hover:bg-slate-800 hover:text-white'}`}><Icon className="w-4 h-4" />{item.label}</Link>;
            })}
          </nav>
        </ScrollArea>
        <Separator className="bg-slate-700" />
        <div className="p-4 space-y-3">
          <div className="flex items-center gap-2 text-sm text-slate-400">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center text-xs">{user?.username?.[0]?.toUpperCase() || 'U'}</div>
            <div className="flex-1 min-w-0">
              <p className="truncate text-white">{user?.username || 'User'}</p>
              <p className="truncate text-xs">{user?.email}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-1">
            {user?.roles?.map(r => <Badge key={r} variant="outline" className="text-[10px] border-slate-600 text-slate-400">{r}</Badge>)}
          </div>
          <Button variant="ghost" size="sm" className="w-full text-slate-400 hover:text-white hover:bg-slate-800" onClick={handleLogout}><LogOut className="w-4 h-4 mr-2" />Выход</Button>
        </div>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 bg-white border-b flex items-center justify-between px-6">
          <h1 className="text-lg font-semibold text-slate-800">{navItems.find(n => n.path === location.pathname)?.label || 'FitIntel'}</h1>
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" className="relative"><Bell className="w-5 h-5" /><span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" /></Button>
            <Badge variant="secondary" className="bg-emerald-100 text-emerald-700">Online</Badge>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6"><Outlet /></main>
      </div>
    </div>
  );
}
"@
Set-Content -Path "src/layouts/AdminLayout.tsx" -Value $adminLayout -Encoding UTF8

$clientLayout = @"import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LogOut, User, CreditCard, DoorOpen, Wallet, Dumbbell } from 'lucide-react';

const clientNav = [
  { path: '/cabinet', label: 'Профиль', icon: User },
  { path: '/cabinet/subscriptions', label: 'Абонементы', icon: CreditCard },
  { path: '/cabinet/visits', label: 'Посещения', icon: DoorOpen },
  { path: '/cabinet/wallet', label: 'Кошелек', icon: Wallet },
];

export default function ClientLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-emerald-500 rounded-lg flex items-center justify-center"><Dumbbell className="w-5 h-5 text-white" /></div>
            <span className="font-bold text-lg">FitIntel</span>
            <Badge variant="outline" className="text-emerald-600">Личный кабинет</Badge>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-slate-600">{user?.username || user?.email}</span>
            <Button variant="ghost" size="sm" onClick={() => { logout(); navigate('/login'); }}><LogOut className="w-4 h-4 mr-1" />Выход</Button>
          </div>
        </div>
      </header>
      <div className="max-w-6xl mx-auto px-4 py-6 flex gap-6">
        <aside className="w-56 shrink-0">
          <nav className="space-y-1 bg-white rounded-xl border p-2">
            {clientNav.map(item => {
              const Icon = item.icon;
              const active = location.pathname === item.path;
              return <Link key={item.path} to={item.path} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors 
${active ? 'bg-emerald-50 text-emerald-700 font-medium' : 'text-slate-600 hover:bg-slate-50'}`}><Icon className="w-4 h-4" />{item.label}</Link>;
            })}
          </nav>
        </aside>
        <main className="flex-1 min-w-0"><Outlet /></main>
      </div>
    </div>
  );
}
"@
Set-Content -Path "src/layouts/ClientLayout.tsx" -Value $clientLayout -Encoding UTF8

# Step 11: Pages
Write-Host "Creating pages..." -ForegroundColor Cyan

$loginPage = @"import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Dumbbell } from 'lucide-react';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();
  const [loginField, setLoginField] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try { await login(loginField, password); navigate('/'); } catch (err: any) { setError(err.response?.data?.detail || 'Ошибка входа'); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100">
      <div className="w-full max-w-sm">
        <div className="flex justify-center mb-6">
          <div className="w-14 h-14 bg-emerald-500 rounded-xl flex items-center justify-center shadow-lg"><Dumbbell className="w-8 h-8 text-white" /></div>
        </div>
        <h1 className="text-2xl font-bold text-center text-slate-800 mb-1">FitIntel Pro</h1>
        <p className="text-sm text-center text-slate-500 mb-6">Вход в систему</p>
        <Card>
          <CardHeader className="pb-3"><CardTitle className="text-base">Авторизация</CardTitle></CardHeader>
          <CardContent>
            {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2"><Label>Логин</Label><Input value={loginField} onChange={e => setLoginField(e.target.value)} placeholder="admin" required /></div>
              <div className="space-y-2"><Label>Пароль</Label><Input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="admin" required /></div>
              <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-700" disabled={isLoading}>{isLoading ? '...' : 'Войти'}</Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
"@
Set-Content -Path "src/pages/auth/LoginPage.tsx" -Value $loginPage -Encoding UTF8

$dashboardPage = @"import { useEffect, useState } from 'react';
import { analyticsApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Users, DoorOpen, CreditCard, Wallet } from 'lucide-react';

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { analyticsApi.dashboard().then(r => setData(r.data)).finally(() => setLoading(false)); }, []);
  const stats = [
    { label: 'Всего клиентов', value: data?.clients?.total || 0, sub: (data?.clients?.active || 0) + ' активных', icon: Users, color: 'bg-blue-50 text-blue-600' },
    { label: 'Посещений сегодня', value: data?.visits_today || 0, sub: 'за сегодня', icon: DoorOpen, color: 'bg-emerald-50 text-emerald-600' },
    { label: 'Активных абонементов', value: data?.subscriptions_active || 0, sub: 'абонементы', icon: CreditCard, color: 'bg-purple-50 text-purple-600' },
    { label: 'Выручка (мес)', value: ((data?.revenue_month || 0)).toLocaleString('ru-RU') + ' ₽', sub: 'с начала месяца', icon: Wallet, color: 'bg-amber-50 text-amber-600' },
  ];
  if (loading) return <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">{[1,2,3,4].map(i => <Skeleton key={i} className="h-28" />)}</div>;
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => {
          const Icon = s.icon;
          return <Card key={s.label}><CardContent className="p-5">
            <div className="flex items-start justify-between">
              <div className="space-y-1"><p className="text-sm text-slate-500">{s.label}</p><p className="text-2xl font-bold text-slate-800">{s.value}</p><p className="text-xs text-slate-400">{s.sub}</p></div>
              <div className={`p-2.5 rounded-lg ${s.color}`}><Icon className="w-5 h-5" /></div>
            </div>
          </CardContent></Card>;
        })}
      </div>
    </div>
  );
}
"@
Set-Content -Path "src/pages/admin/DashboardPage.tsx" -Value $dashboardPage -Encoding UTF8

$clientsPage = @"import { useEffect, useState } from 'react';
import { clientsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Plus, Search, Phone, Mail } from 'lucide-react';

export default function ClientsPage() {
  const [clients, setClients] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [form, setForm] = useState({ first_name: '', last_name: '', phone: '', email: '' });
  const fetch = () => { setLoading(true); clientsApi.list({ limit: 100 }).then(r => setClients(r.data?.items || [])).finally(() => setLoading(false)); };
  useEffect(() => { fetch(); }, []);
  const handleCreate = async (e: React.FormEvent) => { e.preventDefault(); await clientsApi.create({ ...form, is_active: true, status: 'ACTIVE', gender: 'unknown', client_category: 'standard' }); setDialogOpen(false); setForm({ first_name: '', last_name: '', phone: '', email: '' }); fetch(); };
  const filtered = clients.filter(c => `${c.first_name} ${c.last_name} ${c.phone} ${c.email}`.toLowerCase().includes(search.toLowerCase()));
  const statusBadge = (s: string) => { const m: Record<string, string> = { ACTIVE: 'bg-emerald-100 text-emerald-700', BLOCKED: 'bg-red-100 text-red-700', FROZEN: 'bg-blue-100 text-blue-700' }; return <Badge className={m[s] || 'bg-slate-100'}>{s}</Badge>; };
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-sm"><Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" /><Input placeholder="Поиск клиентов..." value={search} onChange={e => setSearch(e.target.value)} className="pl-9" /></div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild><Button className="bg-emerald-600 hover:bg-emerald-700"><Plus className="w-4 h-4 mr-1" />Добавить</Button></DialogTrigger>
          <DialogContent><DialogHeader><DialogTitle>Новый клиент</DialogTitle></DialogHeader>
            <form onSubmit={handleCreate} className="space-y-3">
              <div className="grid grid-cols-2 gap-3"><div className="space-y-1"><Label>Имя</Label><Input required value={form.first_name} onChange={e => setForm({...form, first_name: e.target.value})} /></div><div className="space-y-1"><Label>Фамилия</Label><Input required value={form.last_name} onChange={e => setForm({...form, last_name: e.target.value})} /></div></div>
              <div className="space-y-1"><Label>Телефон</Label><Input required value={form.phone} onChange={e => setForm({...form, phone: e.target.value})} placeholder="+79991234567" /></div>
              <div className="space-y-1"><Label>Email</Label><Input type="email" value={form.email} onChange={e => setForm({...form, email: e.target.value})} /></div>
              <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-700">Создать</Button>
            </form>
          </DialogContent>
        </Dialog>
      </div>
      <Card><CardContent className="p-0">
        {loading ? <div className="p-4 space-y-3">{[1,2,3,4,5].map(i => <Skeleton key={i} className="h-14" />)}</div> : (
          <div className="divide-y">
            {filtered.map(c => (
              <div key={c.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center text-sm font-medium">{c.first_name?.[0]}{c.last_name?.[0]}</div>
                  <div><p className="font-medium text-sm">{c.first_name} {c.last_name}</p><div className="flex gap-3 text-xs text-slate-500"><span className="flex items-center gap-1"><Phone className="w-3 h-3" />{c.phone}</span>{c.email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{c.email}</span>}</div></div>
                </div>
                <div className="flex items-center gap-2">{statusBadge(c.status)}<span className="text-xs text-slate-400">{c.is_active ? 'Активен' : 'Неактивен'}</span></div>
              </div>
            ))}
            {filtered.length === 0 && <p className="p-8 text-center text-slate-400">Клиенты не найдены</p>}
          </div>
        )}
      </CardContent></Card>
    </div>
  );
}
"@
Set-Content -Path "src/pages/admin/ClientsPage.tsx" -Value $clientsPage -Encoding UTF8

$subscriptionsPage = @"import { useEffect, useState } from 'react';
import { subscriptionsApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Pause, Play, RotateCcw, X } from 'lucide-react';

export default function SubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const fetch = () => { setLoading(true); subscriptionsApi.list({ limit: 100 }).then(r => setSubs(r.data?.items || [])).finally(() => setLoading(false)); };
  useEffect(() => { fetch(); }, []);
  const statusMap: Record<string, string> = { ACTIVE: 'bg-emerald-100 text-emerald-700', FROZEN: 'bg-blue-100 text-blue-700', EXPIRED: 'bg-slate-100', CANCELLED: 'bg-red-100 text-red-700' };
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Абонементы</h2>
      {loading ? <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{[1,2,3].map(i => <Skeleton key={i} className="h-40" />)}</div> : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {subs.map(s => (
            <Card key={s.id}><CardContent className="p-4 space-y-3">
              <div className="flex items-center justify-between"><Badge className={statusMap[s.status] || 'bg-slate-100'}>{s.status}</Badge><span className="text-xs text-slate-400">{s.visits_left} визитов</span></div>
              <div><p className="font-medium">{s.tariff_name}</p><p className="text-xs text-slate-500">{s.client_name || s.client_id}</p></div>
              <div className="text-xs text-slate-500"><p>С: {s.start_date || '-'} По: {s.end_date || '-'}</p></div>
              <div className="flex gap-1 pt-1">
                {s.status === 'ACTIVE' && <Button size="sm" variant="outline" onClick={() => subscriptionsApi.freeze(s.id).then(fetch)}><Pause className="w-3 h-3 mr-1" />Заморозить</Button>}
                {s.status === 'FROZEN' && <Button size="sm" variant="outline" onClick={() => subscriptionsApi.unfreeze(s.id).then(fetch)}><Play className="w-3 h-3 mr-1" />Разморозить</Button>}
                <Button size="sm" variant="outline" onClick={() => subscriptionsApi.renew(s.id).then(fetch)}><RotateCcw className="w-3 h-3 mr-1" />Продлить</Button>
                <Button size="sm" variant="outline" className="text-red-600" onClick={() => subscriptionsApi.cancel(s.id).then(fetch)}><X className="w-3 h-3" /></Button>
              </div>
            </CardContent></Card>
          ))}
          {subs.length === 0 && <p className="col-span-full text-center text-slate-400 py-12">Нет абонементов</p>}
        </div>
      )}
    </div>
  );
}
"@
Set-Content -Path "src/pages/admin/SubscriptionsPage.tsx" -Value $subscriptionsPage -Encoding UTF8

$visitsPage = @"import { useEffect, useState } from 'react';
import { visitsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { DoorOpen, DoorClosed, Users, Clock } from 'lucide-react';

export default function VisitsPage() {
  const [activeVisits, setActiveVisits] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [clientId, setClientId] = useState('');
  const [loading, setLoading] = useState(true);
  const fetchData = () => { setLoading(true); Promise.all([visitsApi.active().then(r => setActiveVisits(r.data?.items || [])), visitsApi.statsToday().then(r => setStats(r.data))]).finally(() => setLoading(false)); };
  useEffect(() => { fetchData(); }, []);
  const handleEntry = () => { if (!clientId) return; visitsApi.entry({ client_id: clientId, access_method: 'manual' }).then(fetchData); setClientId(''); };
  const handleExit = (id: string) => { visitsApi.exit({ visit_id: id }).then(fetchData); };
  return (
    <div className="space-y-4">
      <Card><CardContent className="p-4">
        <div className="flex gap-2">
          <Input placeholder="ID клиента или QR..." value={clientId} onChange={e => setClientId(e.target.value)} />
          <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handleEntry}><DoorOpen className="w-4 h-4 mr-1" />Вход</Button>
        </div>
      </CardContent></Card>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card><CardContent className="p-4 flex items-center gap-3"><div className="p-2 bg-emerald-50 rounded-lg"><Users className="w-5 h-5 text-emerald-600" /></div><div><p className="text-sm text-slate-500">В зале сейчас</p><p className="text-xl font-bold">{activeVisits.length}</p></div></CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3"><div className="p-2 bg-blue-50 rounded-lg"><DoorOpen className="w-5 h-5 text-blue-600" /></div><div><p className="text-sm text-slate-500">Входов сегодня</p><p className="text-xl font-bold">{stats?.entries || 0}</p></div></CardContent></Card>
        <Card><CardContent className="p-4 flex items-center gap-3"><div className="p-2 bg-amber-50 rounded-lg"><Clock className="w-5 h-5 text-amber-600" /></div><div><p className="text-sm text-slate-500">Ср. время</p><p className="text-xl font-bold">{stats?.avg_duration ? Math.round(stats.avg_duration) + ' мин' : '-'}</p></div></CardContent></Card>
      </div>
      <Card><CardContent className="p-0">
        {loading ? <div className="p-4 space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-14" />)}</div> : (
          <div className="divide-y">
            {activeVisits.map(v => (
              <div key={v.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                <div><p className="font-medium text-sm">{v.client_name || v.client_id}</p><p className="text-xs text-slate-500">Вход: {v.entry_time ? new Date(v.entry_time).toLocaleTimeString('ru-RU') : '-'}</p></div>
                <div className="flex items-center gap-2"><Badge variant="outline" className="text-emerald-600">В зале</Badge><Button size="sm" variant="outline" onClick={() => handleExit(v.id)}><DoorClosed className="w-3 h-3 mr-1" />Выход</Button></div>
              </div>
            ))}
            {activeVisits.length === 0 && <p className="p-8 text-center text-slate-400">Нет активных посещений</p>}
          </div>
        )}
      </CardContent></Card>
    </div>
  );
}
"@
Set-Content -Path "src/pages/admin/VisitsPage.tsx" -Value $visitsPage -Encoding UTF8

$financePage = @"import { useEffect, useState } from 'react';
import { financeApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { Wallet, CreditCard, Receipt } from 'lucide-react';

export default function FinancePage() {
  const [wallet, setWallet] = useState<any>(null);
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { Promise.all([financeApi.walletMe().then(r => setWallet(r.data)), financeApi.payments().then(r => setPayments(r.data?.items || []))]).finally(() => setLoading(false)); }, []);
  const statusMap: Record<string, string> = { PENDING: 'bg-amber-100 text-amber-700', COMPLETED: 'bg-emerald-100 text-emerald-700', FAILED: 'bg-red-100 text-red-700', REFUNDED: 'bg-slate-100' };
  return (
    <Tabs defaultValue="wallet" className="space-y-4">
      <TabsList>
        <TabsTrigger value="wallet"><Wallet className="w-4 h-4 mr-1" />Кошельки</TabsTrigger>
        <TabsTrigger value="payments"><CreditCard className="w-4 h-4 mr-1" />Платежи</TabsTrigger>
        <TabsTrigger value="receipts"><Receipt className="w-4 h-4 mr-1" />Чеки</TabsTrigger>
      </TabsList>
      <TabsContent value="wallet" className="space-y-4">
        {loading ? <Skeleton className="h-32" /> : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card><CardContent className="p-5"><p className="text-sm text-slate-500">Баланс</p><p className="text-2xl font-bold">{wallet?.balance || 0} {wallet?.currency || 'RUB'}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-sm text-slate-500">Заморожено</p><p className="text-2xl font-bold">{wallet?.frozen_balance || 0}</p></CardContent></Card>
            <Card><CardContent className="p-5"><p className="text-sm text-slate-500">Транзакций</p><p className="text-2xl font-bold">{wallet?.transaction_count || 0}</p></CardContent></Card>
          </div>
        )}
      </TabsContent>
      <TabsContent value="payments">
        <Card><CardContent className="p-0">
          {loading ? <div className="p-4 space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-14" />)}</div> : (
            <div className="divide-y">
              {payments.map(p => (
                <div key={p.id} className="p-4 flex items-center justify-between hover:bg-slate-50">
                  <div><p className="text-sm font-medium">{p.description || `Платеж #${p.id?.slice(0,8)}`}</p><p className="text-xs text-slate-500">{p.client_name || p.client_id}</p></div>
                  <div className="flex items-center gap-3"><p className="font-semibold">{p.amount} {p.currency || 'RUB'}</p><Badge className={statusMap[p.status] || 'bg-slate-100'}>{p.status}</Badge></div>
                </div>
              ))}
              {payments.length === 0 && <p className="p-8 text-center text-slate-400">Нет платежей</p>}
            </div>
          )}
        </CardContent></Card>
      </TabsContent>
      <TabsContent value="receipts"><Card><CardContent className="p-8 text-center text-slate-400"><Receipt className="w-12 h-12 mx-auto mb-3 opacity-50" /><p>Выберите платеж для просмотра чека</p></CardContent></Card></TabsContent>
    </Tabs>
  );
}
"@
Set-Content -Path "src/pages/admin/FinancePage.tsx" -Value $financePage -Encoding UTF8

$accessPage = @"import { useState } from 'react';
import { accessApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { QrCode, DoorOpen, Lock } from 'lucide-react';

export default function AccessPage() {
  const [credential, setCredential] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [result, setResult] = useState<any>(null);
  const handleCheck = async () => { if (!credential) return; const res = await accessApi.check({ credential, device_id: deviceId || undefined }); setResult(res.data); };
  const handleGrant = async () => { if (!credential) return; await accessApi.grant({ credential, device_id: deviceId || undefined }); setResult({ allowed: true, message: 'Доступ предоставлен' }); };
  return (
    <Tabs defaultValue="check" className="space-y-4">
      <TabsList>
        <TabsTrigger value="check"><DoorOpen className="w-4 h-4 mr-1" />Проверка</TabsTrigger>
        <TabsTrigger value="credentials"><QrCode className="w-4 h-4 mr-1" />Ключи</TabsTrigger>
        <TabsTrigger value="lockers"><Lock className="w-4 h-4 mr-1" />Шкафчики</TabsTrigger>
      </TabsList>
      <TabsContent value="check">
        <Card><CardContent className="p-4 space-y-3">
          <Input placeholder="QR-код или RFID..." value={credential} onChange={e => setCredential(e.target.value)} />
          <Input placeholder="ID устройства (опц.)" value={deviceId} onChange={e => setDeviceId(e.target.value)} />
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleCheck}>Проверить</Button>
            <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handleGrant}><DoorOpen className="w-4 h-4 mr-1" />Открыть</Button>
          </div>
          {result && <div className={`p-3 rounded-lg ${result.allowed ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-700'}`}><p className="font-medium">{result.allowed ? 'Доступ разрешен' : 'Доступ запрещен'}</p>{result.message && <p className="text-sm">{result.message}</p>}</div>}
        </CardContent></Card>
      </TabsContent>
      <TabsContent value="credentials"><Card><CardContent className="p-8 text-center text-slate-400">Управление ключами доступа</CardContent></Card></TabsContent>
      <TabsContent value="lockers"><Card><CardContent className="p-8 text-center text-slate-400">Управление шкафчиками</CardContent></Card></TabsContent>
    </Tabs>
  );
}
"@
Set-Content -Path "src/pages/admin/AccessPage.tsx" -Value $accessPage -Encoding UTF8

$devicesPage = @"import { useEffect, useState } from 'react';
import { devicesApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Wifi, WifiOff } from 'lucide-react';

export default function DevicesPage() {
  const [devices, setDevices] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const fetch = () => { setLoading(true); devicesApi.list().then(r => setDevices(r.data?.items || [])).finally(() => setLoading(false)); };
  useEffect(() => { fetch(); }, []);
  const isOnline = (lp: string | null) => { if (!lp) return false; return Date.now() - new Date(lp).getTime() < 5 * 60 * 1000; };
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Устройства</h2><Button size="sm" variant="outline" onClick={fetch}>Обновить</Button></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? [1,2,3].map(i => <Skeleton key={i} className="h-32" />) : devices.map(d => {
          const online = isOnline(d.last_ping);
          return <Card key={d.id}><CardContent className="p-4 space-y-2">
            <div className="flex items-center justify-between"><p className="font-medium">{d.name}</p>{online ? <Wifi className="w-4 h-4 text-emerald-500" /> : <WifiOff className="w-4 h-4 text-red-500" />}</div>
            <p className="text-xs text-slate-500">{d.device_type} — {d.location}</p>
            <Badge className={online ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{online ? 'Онлайн' : 'Оффлайн'}</Badge>
            <p className="text-xs text-slate-400">Last ping: {d.last_ping ? new Date(d.last_ping).toLocaleString('ru-RU') : 'Никогда'}</p>
          </CardContent></Card>;
        })}
        {!loading && devices.length === 0 && <Card className="col-span-full"><CardContent className="p-8 text-center text-slate-400">Нет устройств</CardContent></Card>}
      </div>
    </div>
  );
}
"@
Set-Content -Path "src/pages/admin/DevicesPage.tsx" -Value $devicesPage -Encoding UTF8

$analyticsPage = @"import { useState } from 'react';
import { analyticsApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { BarChart3 } from 'lucide-react';

export default function AnalyticsPage() {
  const [start, setStart] = useState(''); const [end, setEnd] = useState(''); const [data, setData] = useState<any>(null); const [loading, setLoading] = useState(false);
  const fetchVisits = () => { if (!start || !end) return; setLoading(true); analyticsApi.visits(start, end).then(r => setData(r.data)).finally(() => setLoading(false)); };
  const maxVisits = Math.max(...(data?.daily?.map((d: any) => d.visits) || [1]), 1);
  return (
    <div className="space-y-4">
      <Card><CardContent className="p-4 space-y-3">
        <p className="font-medium">Аналитика посещений</p>
        <div className="flex gap-2">
          <Input type="date" value={start} onChange={e => setStart(e.target.value)} />
          <Input type="date" value={end} onChange={e => setEnd(e.target.value)} />
          <Button onClick={fetchVisits} className="bg-emerald-600 hover:bg-emerald-700"><BarChart3 className="w-4 h-4 mr-1" />Показать</Button>
        </div>
        {loading && <Skeleton className="h-48" />}
        {data && !loading && (
          <div className="space-y-2">
            <p className="text-sm">Всего посещений: <strong>{data.total_visits}</strong></p>
            {data.daily?.map((day: any) => (
              <div key={day.day} className="flex items-center gap-3">
                <span className="text-xs w-20 text-slate-500">{new Date(day.day).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })}</span>
                <div className="flex-1 bg-slate-100 rounded-full h-6 overflow-hidden"><div className="bg-emerald-500 h-full rounded-full flex items-center justify-end pr-2" style={{ width: Math.max((day.visits / maxVisits) * 100, 5) + '%' }}><span className="text-[10px] text-white">{day.visits}</span></div></div>
                <span className="text-xs w-10 text-slate-400">{day.unique_clients} чел</span>
              </div>
            ))}
          </div>
        )}
      </CardContent></Card>
    </div>
  );
}
"@
Set-Content -Path "src/pages/admin/AnalyticsPage.tsx" -Value $analyticsPage -Encoding UTF8

$settingsPage = @"import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { useAuthStore } from '@/store/authStore';
import { Shield, Server } from 'lucide-react';

export default function SettingsPage() {
  const { user } = useAuthStore();
  return (
    <div className="max-w-2xl space-y-4">
      <Card><CardContent className="p-4 space-y-3">
        <p className="font-medium flex items-center gap-2"><Shield className="w-4 h-4" />Мой профиль</p>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div><span className="text-slate-500">ID:</span> <span className="font-mono text-xs">{user?.id}</span></div>
          <div><span className="text-slate-500">Логин:</span> {user?.username || '-'}</div>
          <div><span className="text-slate-500">Email:</span> {user?.email || '-'}</div>
          <div><span className="text-slate-500">Статус:</span> <Badge>{user?.is_active ? 'Активен' : 'Неактивен'}</Badge></div>
        </div>
        <Separator />
        <div><span className="text-sm text-slate-500">Роли:</span><div className="flex flex-wrap gap-1 mt-1">{user?.roles?.map(r => <Badge key={r} variant="outline">{r}</Badge>)}</div></div>
        <div><span className="text-sm text-slate-500">Права ({user?.permissions?.length || 0}):</span><div className="flex flex-wrap gap-1 mt-1 max-h-24 overflow-y-auto">{user?.permissions?.map(p => <Badge key={p} variant="secondary" className="text-[10px]">{p}</Badge>)}</div></div>
      </CardContent></Card>
      <Card><CardContent className="p-4 space-y-2">
        <p className="font-medium flex items-center gap-2"><Server className="w-4 h-4" />Система</p>
        <div className="flex justify-between text-sm"><span className="text-slate-500">Версия API</span><span>v1.0.0</span></div>
        <div className="flex justify-between text-sm"><span className="text-slate-500">Среда</span><Badge>production</Badge></div>
      </CardContent></Card>
    </div>
  );
}
"@
Set-Content -Path "src/pages/admin/SettingsPage.tsx" -Value $settingsPage -Encoding UTF8

# Step 12: Client pages
$clientProfile = @"import { useEffect, useState } from 'react';
import { selfserviceApi } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { User, Wallet, CreditCard, Calendar } from 'lucide-react';

export default function ProfilePage() {
  const { user } = useAuthStore();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => { selfserviceApi.profile().then(r => setProfile(r.data)).finally(() => setLoading(false)); }, []);
  if (loading) return <div className="space-y-4"><Skeleton className="h-32" /><Skeleton className="h-32" /></div>;
  return (
    <div className="space-y-4">
      <Card><CardContent className="p-4 space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center justify-center text-xl font-bold text-emerald-700">{profile?.client?.first_name?.[0] || user?.username?.[0] || '?'}</div>
          <div><p className="font-semibold text-lg">{profile?.client?.first_name} {profile?.client?.last_name}</p><p className="text-sm text-slate-500">{user?.email}</p><Badge className="mt-1">{profile?.client?.status === 'ACTIVE' ? 'Активен' : profile?.client?.status}</Badge></div>
        </div>
      </CardContent></Card>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card><CardContent className="p-5"><div className="flex items-center gap-3"><div className="p-2 bg-emerald-50 rounded-lg"><Wallet className="w-5 h-5 text-emerald-600" /></div><div><p className="text-sm text-slate-500">Баланс</p><p className="text-xl font-bold">{profile?.wallet?.balance || 0} {profile?.wallet?.currency || 'RUB'}</p></div></div></CardContent></Card>
        <Card><CardContent className="p-5"><div className="flex items-center gap-3"><div className="p-2 bg-blue-50 rounded-lg"><CreditCard className="w-5 h-5 text-blue-600" /></div><div><p className="text-sm text-slate-500">Абонементов</p><p className="text-xl font-bold">{profile?.subscriptions?.length || 0}</p></div></div></CardContent></Card>
      </div>
    </div>
  );
}
"@
Set-Content -Path "src/pages/client/ProfilePage.tsx" -Value $clientProfile -Encoding UTF8

$clientSubs = @"import { useEffect, useState } from 'react';
import { selfserviceApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { CreditCard, Calendar } from 'lucide-react';

export default function ClientSubscriptionsPage() {
  const [subs, setSubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { selfserviceApi.subscriptions().then(r => setSubs(r.data?.items || [])).finally(() => setLoading(false)); }, []);
  const statusMap: Record<string, string> = { ACTIVE: 'bg-emerald-100 text-emerald-700', FROZEN: 'bg-blue-100 text-blue-700', EXPIRED: 'bg-slate-100', CANCELLED: 'bg-red-100 text-red-700' };
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold flex items-center gap-2"><CreditCard className="w-5 h-5" />Мои абонементы</h2>
      {loading ? <div className="space-y-3">{[1,2].map(i => <Skeleton key={i} className="h-28" />)}</div> : (
        <div className="space-y-3">
          {subs.map(s => <Card key={s.id}><CardContent className="p-4 space-y-2">
            <div className="flex items-center justify-between"><p className="font-medium">{s.tariff_name}</p><Badge className={statusMap[s.status] || 'bg-slate-100'}>{s.status}</Badge></div>
            <div className="text-sm text-slate-500"><p className="flex items-center gap-2"><Calendar className="w-3 h-3" />{s.start_date} — {s.end_date}</p><p>Осталось визитов: {s.visits_left}</p>{s.freeze_until && <p className="text-blue-600">Заморожен до: {s.freeze_until}</p>}</div>
          </CardContent></Card>)}
          {subs.length === 0 && <Card><CardContent className="p-8 text-center text-slate-400">Нет абонементов</CardContent></Card>}
        </div>
      )}
    </div>
  );
}
"@
Set-Content -Path "src/pages/client/ClientSubscriptionsPage.tsx" -Value $clientSubs -Encoding UTF8

$clientVisits = @"import { useEffect, useState } from 'react';
import { selfserviceApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { DoorOpen, Clock } from 'lucide-react';

export default function ClientVisitsPage() {
  const [visits, setVisits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { selfserviceApi.visits().then(r => setVisits(r.data?.items || [])).finally(() => setLoading(false)); }, []);
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold flex items-center gap-2"><DoorOpen className="w-5 h-5" />Мои посещения</h2>
      {loading ? <div className="space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-16" />)}</div> : (
        <div className="space-y-2">
          {visits.map(v => <Card key={v.id}><CardContent className="p-4 flex items-center justify-between">
            <div className="text-sm">
              <p className="font-medium">{new Date(v.entry_time).toLocaleDateString('ru-RU', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
              <p className="text-slate-500 text-xs">{new Date(v.entry_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })} — {v.exit_time ? new Date(v.exit_time).toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' }) : 'В зале'}</p>
            </div>
            <div className="flex items-center gap-1 text-sm text-slate-600"><Clock className="w-4 h-4" />{v.duration_minutes ? v.duration_minutes + ' мин' : '—'}</div>
          </CardContent></Card>)}
          {visits.length === 0 && <Card><CardContent className="p-8 text-center text-slate-400">Нет посещений</CardContent></Card>}
        </div>
      )}
    </div>
  );
}
"@
Set-Content -Path "src/pages/client/ClientVisitsPage.tsx" -Value $clientVisits -Encoding UTF8

$clientWallet = @"import { useEffect, useState } from 'react';
import { financeApi } from '@/lib/api';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Wallet, ArrowDownLeft, ArrowUpRight } from 'lucide-react';

export default function ClientWalletPage() {
  const [wallet, setWallet] = useState<any>(null);
  const [txs, setTxs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => { Promise.all([financeApi.walletMe().then(r => setWallet(r.data)), financeApi.walletTransactions().then(r => setTxs(r.data?.items || []))]).finally(() => setLoading(false)); }, []);
  return (
    <div className="space-y-4">
      {loading ? <Skeleton className="h-32" /> : <Card className="bg-emerald-600 text-white"><CardContent className="p-6">
        <div className="flex items-center justify-between">
          <div><p className="text-emerald-100 text-sm">Баланс кошелька</p><p className="text-3xl font-bold">{wallet?.balance || 0} {wallet?.currency || 'RUB'}</p></div>
          <Wallet className="w-10 h-10 text-emerald-200" />
        </div>
      </CardContent></Card>}
      <h3 className="font-medium text-slate-700">История операций</h3>
      {loading ? <div className="space-y-3">{[1,2,3].map(i => <Skeleton key={i} className="h-14" />)}</div> : (
        <div className="space-y-2">
          {txs.map(tx => <Card key={tx.id}><CardContent className="p-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-1.5 rounded-full ${tx.amount > 0 ? 'bg-emerald-50' : 'bg-red-50'}`}>{tx.amount > 0 ? <ArrowDownLeft className="w-4 h-4 text-emerald-600" /> : <ArrowUpRight className="w-4 h-4 text-red-600" />}</div>
              <div className="text-sm"><p>{tx.description || tx.type}</p><p className="text-xs text-slate-500">{tx.created_at ? new Date(tx.created_at).toLocaleDateString('ru-RU') : ''}</p></div>
            </div>
            <span className={`font-medium ${tx.amount > 0 ? 'text-emerald-600' : 'text-red-600'}`}>{tx.amount > 0 ? '+' : ''}{tx.amount} {tx.currency || 'RUB'}</span>
          </CardContent></Card>)}
          {txs.length === 0 && <p className="text-center text-slate-400 py-8">Нет операций</p>}
        </div>
      )}
    </div>
  );
}
"@
Set-Content -Path "src/pages/client/ClientWalletPage.tsx" -Value $clientWallet -Encoding UTF8

# Step 13: App.tsx with routing
Write-Host "Creating App.tsx with routing..." -ForegroundColor Cyan

$appContent = @"import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';
import AdminLayout from '@/layouts/AdminLayout';
import ClientLayout from '@/layouts/ClientLayout';
import LoginPage from '@/pages/auth/LoginPage';
import DashboardPage from '@/pages/admin/DashboardPage';
import ClientsPage from '@/pages/admin/ClientsPage';
import SubscriptionsPage from '@/pages/admin/SubscriptionsPage';
import VisitsPage from '@/pages/admin/VisitsPage';
import FinancePage from '@/pages/admin/FinancePage';
import AccessPage from '@/pages/admin/AccessPage';
import SettingsPage from '@/pages/admin/SettingsPage';
import DevicesPage from '@/pages/admin/DevicesPage';
import AnalyticsPage from '@/pages/admin/AnalyticsPage';
import ProfilePage from '@/pages/client/ProfilePage';
import ClientSubscriptionsPage from '@/pages/client/ClientSubscriptionsPage';
import ClientVisitsPage from '@/pages/client/ClientVisitsPage';
import ClientWalletPage from '@/pages/client/ClientWalletPage';

function AuthGuard({ children, requireAdmin = false }: { children: React.ReactNode; requireAdmin?: boolean }) {
  const { isAuthenticated, user, isLoading } = useAuthStore();
  if (isLoading) return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-8 h-8 border-4 border-emerald-500 border-t-transparent rounded-full" /></div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (requireAdmin && !user?.roles?.some((r: string) => ['owner','admin','manager'].includes(r))) return <Navigate to="/cabinet" replace />;
  return <>{children}</>;
}

function RedirectByRole() {
  const { user } = useAuthStore();
  const isAdmin = user?.roles?.some((r: string) => ['owner','admin','manager','cashier','trainer','support'].includes(r));
  return isAdmin ? <Navigate to="/" replace /> : <Navigate to="/cabinet" replace />;
}

export default function App() {
  const { isAuthenticated, fetchMe } = useAuthStore();
  useEffect(() => { if (isAuthenticated) fetchMe(); }, [isAuthenticated]);
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<AuthGuard requireAdmin><AdminLayout /></AuthGuard>}>
          <Route index element={<DashboardPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="subscriptions" element={<SubscriptionsPage />} />
          <Route path="visits" element={<VisitsPage />} />
          <Route path="finance" element={<FinancePage />} />
          <Route path="access" element={<AccessPage />} />
          <Route path="devices" element={<DevicesPage />} />
          <Route path="analytics" element={<AnalyticsPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="/cabinet" element={<AuthGuard><ClientLayout /></AuthGuard>}>
          <Route index element={<ProfilePage />} />
          <Route path="subscriptions" element={<ClientSubscriptionsPage />} />
          <Route path="visits" element={<ClientVisitsPage />} />
          <Route path="wallet" element={<ClientWalletPage />} />
        </Route>
        <Route path="*" element={<RedirectByRole />} />
      </Routes>
    </BrowserRouter>
  );
}
"@
Set-Content -Path "src/App.tsx" -Value $appContent -Encoding UTF8

# Step 14: Update vite.config for path alias
Write-Host "Configuring vite..." -ForegroundColor Cyan
$viteConfig = @"import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
  },
})
"@
Set-Content -Path "vite.config.ts" -Value $viteConfig -Encoding UTF8

# Step 15: Update tsconfig
$tsConfig = @"{
  " + '"compilerOptions": {' + "
    " + '"target": "ES2020",' + "
    " + '"useDefineForClassFields": true,' + "
    " + '"lib": ["ES2020", "DOM", "DOM.Iterable"],' + "
    " + '"module": "ESNext",' + "
    " + '"skipLibCheck": true,' + "
    " + '"moduleResolution": "bundler",' + "
    " + '"allowImportingTsExtensions": true,' + "
    " + '"resolveJsonModule": true,' + "
    " + '"isolatedModules": true,' + "
    " + '"noEmit": true,' + "
    " + '"jsx": "react-jsx",' + "
    " + '"strict": false,' + "
    " + '"noUnusedLocals": false,' + "
    " + '"noUnusedParameters": false,' + "
    " + '"baseUrl": ".",' + "
    " + '"paths": { "@/*": ["src/*"] }' + "
  },
  " + '"include": ["src"],' + "
  " + '"references": [{ "path": "./tsconfig.node.json" }]' + "
}" + "
"@
Set-Content -Path "tsconfig.json" -Value $tsConfig -Encoding UTF8

# Step 16: Update main.tsx
$mainContent = @"import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"@
Set-Content -Path "src/main.tsx" -Value $mainContent -Encoding UTF8

# Step 17: Remove StrictMode from tsconfig
Write-Host "Building..." -ForegroundColor Green

# Build
npm run build

Write-Host "" -ForegroundColor Green
Write-Host "=== INSTALL COMPLETE ===" -ForegroundColor Green
Write-Host "Run: npm run dev" -ForegroundColor Cyan
Write-Host "Open: http://localhost:5173" -ForegroundColor Cyan
Write-Host "Login: admin / admin" -ForegroundColor Cyan
"@
Set-Content -Path "install-frontend.ps1" -Value $installScript -Encoding UTF8

Write-Host "Script created successfully!" -ForegroundColor Green
