import { useState, type FormEvent } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Settings,
  Plus,
  Pencil,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Copy,
  Sparkles,
  Key,
  Plug,
  Users,
  BarChart3,
  Target,
  Shield,
  Save,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuth, useRequireRole } from "@/hooks/use-auth";
import {
  getQualityParameters,
  createQualityParameter,
  updateQualityParameter,
  deleteQualityParameter,
  seedQualityParameters,
  getIntentSignals,
  createIntentSignal,
  updateIntentSignal,
  deleteIntentSignal,
  seedIntentSignals,
  getPersonaTypes,
  createPersonaType,
  updatePersonaType,
  deletePersonaType,
  getIntegrations,
  createIntegration,
  updateIntegration,
  deleteIntegration,
  getApiKeys,
  createApiKey,
  deleteApiKey,
  getUsers,
  createUser,
  updateUser,
} from "@/lib/api";
import type {
  QualityParameter,
  CreateQualityParameterRequest,
  UpdateQualityParameterRequest,
  IntentSignalConfig,
  CreateIntentSignalRequest,
  UpdateIntentSignalRequest,
  PersonaType,
  CreatePersonaTypeRequest,
  UpdatePersonaTypeRequest,
  Integration,
  CreateIntegrationRequest,
  UpdateIntegrationRequest,
  CreateApiKeyRequest,
  CreateApiKeyResponse,
  User,
  CreateUserRequest,
  UpdateUserRequest,
  UserRole,
  IntegrationType,
} from "@/lib/types";

// ────────────────────────────────────────────────────────────────────
// Settings Page
// ────────────────────────────────────────────────────────────────────

type SettingsTab =
  | "quality"
  | "intent"
  | "personas"
  | "integrations"
  | "users";

const TAB_CONFIG: Array<{
  id: SettingsTab;
  label: string;
  icon: React.ReactNode;
  adminOnly: boolean;
}> = [
  { id: "quality", label: "Quality Parameters", icon: <BarChart3 className="h-4 w-4" />, adminOnly: false },
  { id: "intent", label: "Intent Signals", icon: <Target className="h-4 w-4" />, adminOnly: false },
  { id: "personas", label: "Persona Types", icon: <Shield className="h-4 w-4" />, adminOnly: false },
  { id: "integrations", label: "Integrations", icon: <Plug className="h-4 w-4" />, adminOnly: false },
  { id: "users", label: "Users", icon: <Users className="h-4 w-4" />, adminOnly: true },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<SettingsTab>("quality");
  const isAdmin = useRequireRole(["admin"]);

  const visibleTabs = TAB_CONFIG.filter(
    (tab) => !tab.adminOnly || isAdmin,
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="flex items-center gap-2 text-2xl font-bold text-white">
          <Settings className="h-6 w-6 text-slate-400" />
          Settings
        </h1>
        <p className="mt-1 text-sm text-slate-400">
          Configure quality parameters, intent signals, personas, and
          integrations
        </p>
      </div>

      {/* Tab navigation */}
      <div className="flex gap-1 overflow-x-auto border-b border-slate-800 pb-px">
        {visibleTabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "flex items-center gap-2 whitespace-nowrap border-b-2 px-4 py-2.5 text-sm font-medium transition-colors",
              activeTab === tab.id
                ? "border-accent-500 text-accent-400"
                : "border-transparent text-slate-500 hover:text-slate-300",
            )}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in">
        {activeTab === "quality" && <QualityParametersTab />}
        {activeTab === "intent" && <IntentSignalsTab />}
        {activeTab === "personas" && <PersonaTypesTab />}
        {activeTab === "integrations" && <IntegrationsTab />}
        {activeTab === "users" && isAdmin && <UsersTab />}
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Quality Parameters Tab
// ────────────────────────────────────────────────────────────────────

function QualityParametersTab() {
  const queryClient = useQueryClient();
  const [editItem, setEditItem] = useState<QualityParameter | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: parameters, isLoading } = useQuery({
    queryKey: ["quality-parameters"],
    queryFn: getQualityParameters,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteQualityParameter,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["quality-parameters"] }),
  });

  const seedMutation = useMutation({
    mutationFn: seedQualityParameters,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["quality-parameters"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Configure the parameters used to score call quality.
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors disabled:opacity-60"
          >
            {seedMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            Seed Defaults
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Parameter
          </button>
        </div>
      </div>

      {isLoading ? (
        <SettingsTableSkeleton />
      ) : !parameters || parameters.length === 0 ? (
        <EmptyState message="No quality parameters configured yet. Click 'Seed Defaults' to get started." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-850/80">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Name
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Category
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Weight
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Active
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Order
                </th>
                <th className="w-20 px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {parameters.map((param) => (
                <tr
                  key={param.id}
                  className="transition-colors hover:bg-slate-800/30"
                >
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-white">
                      {param.name}
                    </p>
                    <p className="mt-0.5 text-xs text-slate-500 line-clamp-1">
                      {param.description}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                      {param.category}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-300">
                    {param.weight}
                  </td>
                  <td className="px-4 py-3">
                    <ActiveDot active={param.is_active} />
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {param.display_order}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <IconButton
                        icon={<Pencil className="h-3.5 w-3.5" />}
                        onClick={() => setEditItem(param)}
                        label="Edit"
                      />
                      <IconButton
                        icon={<Trash2 className="h-3.5 w-3.5" />}
                        onClick={() => {
                          if (confirm(`Delete "${param.name}"?`)) {
                            deleteMutation.mutate(param.id);
                          }
                        }}
                        label="Delete"
                        variant="danger"
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit dialog */}
      {(showCreate || editItem) && (
        <QualityParamDialog
          item={editItem}
          onClose={() => {
            setShowCreate(false);
            setEditItem(null);
          }}
        />
      )}
    </div>
  );
}

function QualityParamDialog({
  item,
  onClose,
}: {
  item: QualityParameter | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!item;

  const [name, setName] = useState(item?.name ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [category, setCategory] = useState(item?.category ?? "");
  const [weight, setWeight] = useState(item?.weight ?? 1);
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const [displayOrder, setDisplayOrder] = useState(item?.display_order ?? 0);
  const [formError, setFormError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: (data: CreateQualityParameterRequest) =>
      createQualityParameter(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quality-parameters"] });
      onClose();
    },
    onError: () => setFormError("Failed to create parameter."),
  });

  const updateMut = useMutation({
    mutationFn: (data: UpdateQualityParameterRequest) =>
      updateQualityParameter(item!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["quality-parameters"] });
      onClose();
    },
    onError: () => setFormError("Failed to update parameter."),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !category.trim()) {
      setFormError("Name and category are required.");
      return;
    }
    const payload = {
      name,
      description,
      category,
      weight,
      is_active: isActive,
      display_order: displayOrder,
    };
    if (isEdit) {
      updateMut.mutate(payload);
    } else {
      createMut.mutate(payload);
    }
  };

  const isPending = createMut.isPending || updateMut.isPending;

  return (
    <DialogShell
      title={isEdit ? "Edit Quality Parameter" : "Create Quality Parameter"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {formError && <FormError message={formError} />}
        <FormField label="Name" required>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="settings-input"
            placeholder="e.g., Objection Handling"
          />
        </FormField>
        <FormField label="Description">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="settings-input min-h-[60px] resize-y"
            placeholder="What this parameter measures..."
          />
        </FormField>
        <div className="grid grid-cols-3 gap-3">
          <FormField label="Category" required>
            <input
              type="text"
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="settings-input"
              placeholder="e.g., Communication"
            />
          </FormField>
          <FormField label="Weight">
            <input
              type="number"
              min={0}
              max={1}
              step={0.05}
              value={weight}
              onChange={(e) => setWeight(Number(e.target.value))}
              className="settings-input"
            />
          </FormField>
          <FormField label="Display Order">
            <input
              type="number"
              min={0}
              value={displayOrder}
              onChange={(e) => setDisplayOrder(Number(e.target.value))}
              className="settings-input"
            />
          </FormField>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="rounded border-slate-600"
          />
          Active
        </label>
        <DialogActions onClose={onClose} isPending={isPending} isEdit={isEdit} />
      </form>
    </DialogShell>
  );
}

// ────────────────────────────────────────────────────────────────────
// Intent Signals Tab
// ────────────────────────────────────────────────────────────────────

function IntentSignalsTab() {
  const queryClient = useQueryClient();
  const [editItem, setEditItem] = useState<IntentSignalConfig | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: signals, isLoading } = useQuery({
    queryKey: ["intent-signals"],
    queryFn: getIntentSignals,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteIntentSignal,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["intent-signals"] }),
  });

  const seedMutation = useMutation({
    mutationFn: seedIntentSignals,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["intent-signals"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Configure signals used to detect lead buying intent.
        </p>
        <div className="flex gap-2">
          <button
            onClick={() => seedMutation.mutate()}
            disabled={seedMutation.isPending}
            className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-1.5 text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors disabled:opacity-60"
          >
            {seedMutation.isPending ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Sparkles className="h-3.5 w-3.5" />
            )}
            Seed Defaults
          </button>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Signal
          </button>
        </div>
      </div>

      {isLoading ? (
        <SettingsTableSkeleton />
      ) : !signals || signals.length === 0 ? (
        <EmptyState message="No intent signals configured yet. Click 'Seed Defaults' to get started." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-850/80">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Name
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Description
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Active
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Order
                </th>
                <th className="w-20 px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {signals.map((signal) => (
                <tr
                  key={signal.id}
                  className="transition-colors hover:bg-slate-800/30"
                >
                  <td className="px-4 py-3 text-sm font-medium text-white">
                    {signal.name}
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400 line-clamp-1">
                    {signal.description}
                  </td>
                  <td className="px-4 py-3">
                    <ActiveDot active={signal.is_active} />
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-500">
                    {signal.display_order}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <IconButton
                        icon={<Pencil className="h-3.5 w-3.5" />}
                        onClick={() => setEditItem(signal)}
                        label="Edit"
                      />
                      <IconButton
                        icon={<Trash2 className="h-3.5 w-3.5" />}
                        onClick={() => {
                          if (confirm(`Delete "${signal.name}"?`)) {
                            deleteMutation.mutate(signal.id);
                          }
                        }}
                        label="Delete"
                        variant="danger"
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {(showCreate || editItem) && (
        <IntentSignalDialog
          item={editItem}
          onClose={() => {
            setShowCreate(false);
            setEditItem(null);
          }}
        />
      )}
    </div>
  );
}

function IntentSignalDialog({
  item,
  onClose,
}: {
  item: IntentSignalConfig | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!item;

  const [name, setName] = useState(item?.name ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const [displayOrder, setDisplayOrder] = useState(item?.display_order ?? 0);
  const [formError, setFormError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: (data: CreateIntentSignalRequest) => createIntentSignal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intent-signals"] });
      onClose();
    },
    onError: () => setFormError("Failed to create signal."),
  });

  const updateMut = useMutation({
    mutationFn: (data: UpdateIntentSignalRequest) =>
      updateIntentSignal(item!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["intent-signals"] });
      onClose();
    },
    onError: () => setFormError("Failed to update signal."),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFormError("Name is required.");
      return;
    }
    const payload = { name, description, is_active: isActive, display_order: displayOrder };
    if (isEdit) {
      updateMut.mutate(payload);
    } else {
      createMut.mutate(payload);
    }
  };

  return (
    <DialogShell
      title={isEdit ? "Edit Intent Signal" : "Create Intent Signal"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {formError && <FormError message={formError} />}
        <FormField label="Name" required>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="settings-input"
            placeholder="e.g., Budget mentioned"
          />
        </FormField>
        <FormField label="Description">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="settings-input min-h-[60px] resize-y"
            placeholder="What this signal indicates..."
          />
        </FormField>
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Display Order">
            <input
              type="number"
              min={0}
              value={displayOrder}
              onChange={(e) => setDisplayOrder(Number(e.target.value))}
              className="settings-input"
            />
          </FormField>
          <div className="flex items-end pb-1">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
                className="rounded border-slate-600"
              />
              Active
            </label>
          </div>
        </div>
        <DialogActions onClose={onClose} isPending={createMut.isPending || updateMut.isPending} isEdit={isEdit} />
      </form>
    </DialogShell>
  );
}

// ────────────────────────────────────────────────────────────────────
// Persona Types Tab
// ────────────────────────────────────────────────────────────────────

function PersonaTypesTab() {
  const queryClient = useQueryClient();
  const [editItem, setEditItem] = useState<PersonaType | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: personas, isLoading } = useQuery({
    queryKey: ["persona-types"],
    queryFn: getPersonaTypes,
  });

  const deleteMutation = useMutation({
    mutationFn: deletePersonaType,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["persona-types"] }),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Define persona types based on BANT scoring profiles.
        </p>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Persona
        </button>
      </div>

      {isLoading ? (
        <SettingsTableSkeleton />
      ) : !personas || personas.length === 0 ? (
        <EmptyState message="No persona types configured yet." />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {personas.map((persona) => (
            <div
              key={persona.id}
              className="rounded-xl border border-slate-800 bg-slate-850/60 p-5 transition-colors hover:border-slate-700"
            >
              <div className="flex items-start justify-between">
                <div>
                  <h4 className="text-sm font-semibold text-white">
                    {persona.name}
                  </h4>
                  <p className="mt-1 text-xs text-slate-400">
                    {persona.description}
                  </p>
                </div>
                <ActiveDot active={persona.is_active} />
              </div>
              <div className="mt-3 grid grid-cols-4 gap-2 text-center">
                {(
                  [
                    ["B", persona.bant_profile.min_budget],
                    ["A", persona.bant_profile.min_authority],
                    ["N", persona.bant_profile.min_need],
                    ["T", persona.bant_profile.min_timeline],
                  ] as const
                ).map(([letter, value]) => (
                  <div
                    key={letter}
                    className="rounded-md bg-slate-800/60 px-2 py-1.5"
                  >
                    <p className="text-2xs font-bold text-accent-400">
                      {letter}
                    </p>
                    <p className="text-sm font-semibold text-white">
                      {value}
                    </p>
                  </div>
                ))}
              </div>
              <div className="mt-3 flex gap-1">
                <IconButton
                  icon={<Pencil className="h-3.5 w-3.5" />}
                  onClick={() => setEditItem(persona)}
                  label="Edit"
                />
                <IconButton
                  icon={<Trash2 className="h-3.5 w-3.5" />}
                  onClick={() => {
                    if (confirm(`Delete "${persona.name}"?`)) {
                      deleteMutation.mutate(persona.id);
                    }
                  }}
                  label="Delete"
                  variant="danger"
                />
              </div>
            </div>
          ))}
        </div>
      )}

      {(showCreate || editItem) && (
        <PersonaTypeDialog
          item={editItem}
          onClose={() => {
            setShowCreate(false);
            setEditItem(null);
          }}
        />
      )}
    </div>
  );
}

function PersonaTypeDialog({
  item,
  onClose,
}: {
  item: PersonaType | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!item;

  const [name, setName] = useState(item?.name ?? "");
  const [description, setDescription] = useState(item?.description ?? "");
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const [bantBudget, setBantBudget] = useState(
    item?.bant_profile.min_budget ?? 5,
  );
  const [bantAuthority, setBantAuthority] = useState(
    item?.bant_profile.min_authority ?? 5,
  );
  const [bantNeed, setBantNeed] = useState(item?.bant_profile.min_need ?? 5);
  const [bantTimeline, setBantTimeline] = useState(
    item?.bant_profile.min_timeline ?? 5,
  );
  const [formError, setFormError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: (data: CreatePersonaTypeRequest) => createPersonaType(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["persona-types"] });
      onClose();
    },
    onError: () => setFormError("Failed to create persona type."),
  });

  const updateMut = useMutation({
    mutationFn: (data: UpdatePersonaTypeRequest) =>
      updatePersonaType(item!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["persona-types"] });
      onClose();
    },
    onError: () => setFormError("Failed to update persona type."),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFormError("Name is required.");
      return;
    }
    const payload = {
      name,
      description,
      is_active: isActive,
      bant_profile: {
        min_budget: bantBudget,
        min_authority: bantAuthority,
        min_need: bantNeed,
        min_timeline: bantTimeline,
      },
    };
    if (isEdit) {
      updateMut.mutate(payload);
    } else {
      createMut.mutate(payload);
    }
  };

  return (
    <DialogShell
      title={isEdit ? "Edit Persona Type" : "Create Persona Type"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {formError && <FormError message={formError} />}
        <FormField label="Name" required>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="settings-input"
            placeholder="e.g., Decision Maker"
          />
        </FormField>
        <FormField label="Description">
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="settings-input min-h-[60px] resize-y"
            placeholder="Persona characteristics..."
          />
        </FormField>
        <div>
          <p className="mb-2 text-xs font-medium text-slate-400">
            Minimum BANT Scores (0-10)
          </p>
          <div className="grid grid-cols-4 gap-3">
            <FormField label="Budget">
              <input
                type="number"
                min={0}
                max={10}
                value={bantBudget}
                onChange={(e) => setBantBudget(Number(e.target.value))}
                className="settings-input"
              />
            </FormField>
            <FormField label="Authority">
              <input
                type="number"
                min={0}
                max={10}
                value={bantAuthority}
                onChange={(e) => setBantAuthority(Number(e.target.value))}
                className="settings-input"
              />
            </FormField>
            <FormField label="Need">
              <input
                type="number"
                min={0}
                max={10}
                value={bantNeed}
                onChange={(e) => setBantNeed(Number(e.target.value))}
                className="settings-input"
              />
            </FormField>
            <FormField label="Timeline">
              <input
                type="number"
                min={0}
                max={10}
                value={bantTimeline}
                onChange={(e) => setBantTimeline(Number(e.target.value))}
                className="settings-input"
              />
            </FormField>
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="rounded border-slate-600"
          />
          Active
        </label>
        <DialogActions onClose={onClose} isPending={createMut.isPending || updateMut.isPending} isEdit={isEdit} />
      </form>
    </DialogShell>
  );
}

// ────────────────────────────────────────────────────────────────────
// Integrations Tab
// ────────────────────────────────────────────────────────────────────

function IntegrationsTab() {
  const queryClient = useQueryClient();
  const [editItem, setEditItem] = useState<Integration | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: integrations, isLoading } = useQuery({
    queryKey: ["integrations"],
    queryFn: getIntegrations,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteIntegration,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["integrations"] }),
  });

  return (
    <div className="space-y-6">
      {/* Integrations section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-sm text-slate-400">
            Configure inbound webhooks, outbound CRM sync, and email
            integrations.
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
          >
            <Plus className="h-3.5 w-3.5" />
            Add Integration
          </button>
        </div>

        {isLoading ? (
          <SettingsTableSkeleton />
        ) : !integrations || integrations.length === 0 ? (
          <EmptyState message="No integrations configured yet." />
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {integrations.map((integration) => (
              <div
                key={integration.id}
                className="rounded-xl border border-slate-800 bg-slate-850/60 p-5 transition-colors hover:border-slate-700"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-white">
                      {integration.name}
                    </h4>
                    <span className="mt-1 inline-block rounded bg-primary-600/20 px-2 py-0.5 text-2xs font-medium text-primary-300">
                      {integration.type.replace(/_/g, " ")}
                    </span>
                  </div>
                  <ActiveDot active={integration.is_active} />
                </div>
                <div className="mt-3 space-y-1">
                  {Object.entries(integration.config)
                    .slice(0, 3)
                    .map(([key, value]) => (
                      <div
                        key={key}
                        className="flex items-center gap-2 text-xs"
                      >
                        <span className="text-slate-500">{key}:</span>
                        <span className="truncate text-slate-300">
                          {key.toLowerCase().includes("secret") ||
                          key.toLowerCase().includes("key")
                            ? "***"
                            : value}
                        </span>
                      </div>
                    ))}
                </div>
                {integration.last_synced_at && (
                  <p className="mt-2 text-2xs text-slate-600">
                    Last synced: {new Date(integration.last_synced_at).toLocaleDateString()}
                  </p>
                )}
                <div className="mt-3 flex gap-1">
                  <IconButton
                    icon={<Pencil className="h-3.5 w-3.5" />}
                    onClick={() => setEditItem(integration)}
                    label="Edit"
                  />
                  <IconButton
                    icon={<Trash2 className="h-3.5 w-3.5" />}
                    onClick={() => {
                      if (confirm(`Delete "${integration.name}"?`)) {
                        deleteMutation.mutate(integration.id);
                      }
                    }}
                    label="Delete"
                    variant="danger"
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* API Keys section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-t border-slate-800 pt-6">
          <div>
            <h3 className="flex items-center gap-2 text-sm font-semibold text-white">
              <Key className="h-4 w-4 text-slate-400" />
              API Keys
            </h3>
            <p className="mt-0.5 text-xs text-slate-500">
              Manage API keys for webhook authentication
            </p>
          </div>
          <span className="flex items-center gap-2 text-sm text-slate-500">
            <Key className="h-3.5 w-3.5" />
          </span>
        </div>
        <ApiKeysSection />
      </div>

      {/* Dialogs */}
      {(showCreate || editItem) && (
        <IntegrationDialog
          item={editItem}
          onClose={() => {
            setShowCreate(false);
            setEditItem(null);
          }}
        />
      )}
    </div>
  );
}

function IntegrationDialog({
  item,
  onClose,
}: {
  item: Integration | null;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const isEdit = !!item;

  const [name, setName] = useState(item?.name ?? "");
  const [type, setType] = useState<IntegrationType>(
    item?.type ?? "inbound_webhook",
  );
  const [isActive, setIsActive] = useState(item?.is_active ?? true);
  const [configEntries, setConfigEntries] = useState<
    Array<{ key: string; value: string }>
  >(
    item
      ? Object.entries(item.config).map(([key, value]) => ({ key, value }))
      : [{ key: "", value: "" }],
  );
  const [formError, setFormError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: (data: CreateIntegrationRequest) => createIntegration(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      onClose();
    },
    onError: () => setFormError("Failed to create integration."),
  });

  const updateMut = useMutation({
    mutationFn: (data: UpdateIntegrationRequest) =>
      updateIntegration(item!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["integrations"] });
      onClose();
    },
    onError: () => setFormError("Failed to update integration."),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setFormError("Name is required.");
      return;
    }
    const config: Record<string, string> = {};
    for (const entry of configEntries) {
      if (entry.key.trim()) {
        config[entry.key.trim()] = entry.value;
      }
    }
    const payload = { name, type, is_active: isActive, config };
    if (isEdit) {
      updateMut.mutate(payload);
    } else {
      createMut.mutate(payload);
    }
  };

  return (
    <DialogShell
      title={isEdit ? "Edit Integration" : "Create Integration"}
      onClose={onClose}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {formError && <FormError message={formError} />}
        <div className="grid grid-cols-2 gap-3">
          <FormField label="Name" required>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="settings-input"
              placeholder="My CRM Sync"
            />
          </FormField>
          <FormField label="Type" required>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as IntegrationType)}
              className="settings-input"
            >
              <option value="inbound_webhook">Inbound Webhook</option>
              <option value="outbound_crm">Outbound CRM</option>
              <option value="email">Email</option>
              <option value="slack">Slack</option>
              <option value="custom">Custom</option>
            </select>
          </FormField>
        </div>
        <div>
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-medium text-slate-400">
              Configuration
            </p>
            <button
              type="button"
              onClick={() =>
                setConfigEntries((prev) => [...prev, { key: "", value: "" }])
              }
              className="text-xs text-accent-400 hover:text-accent-300"
            >
              + Add field
            </button>
          </div>
          <div className="space-y-2">
            {configEntries.map((entry, i) => (
              <div key={i} className="flex gap-2">
                <input
                  type="text"
                  value={entry.key}
                  onChange={(e) =>
                    setConfigEntries((prev) =>
                      prev.map((p, j) =>
                        j === i ? { ...p, key: e.target.value } : p,
                      ),
                    )
                  }
                  placeholder="Key"
                  className="settings-input flex-1"
                />
                <input
                  type="text"
                  value={entry.value}
                  onChange={(e) =>
                    setConfigEntries((prev) =>
                      prev.map((p, j) =>
                        j === i ? { ...p, value: e.target.value } : p,
                      ),
                    )
                  }
                  placeholder="Value"
                  className="settings-input flex-1"
                />
                <button
                  type="button"
                  onClick={() =>
                    setConfigEntries((prev) =>
                      prev.filter((_, j) => j !== i),
                    )
                  }
                  className="text-slate-600 hover:text-red-400 transition-colors"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="rounded border-slate-600"
          />
          Active
        </label>
        <DialogActions onClose={onClose} isPending={createMut.isPending || updateMut.isPending} isEdit={isEdit} />
      </form>
    </DialogShell>
  );
}

// ────────────────────────────────────────────────────────────────────
// API Keys Section
// ────────────────────────────────────────────────────────────────────

function ApiKeysSection() {
  const queryClient = useQueryClient();
  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<CreateApiKeyResponse | null>(
    null,
  );
  const [copied, setCopied] = useState(false);

  const { data: apiKeys, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: getApiKeys,
  });

  const createMut = useMutation({
    mutationFn: (data: CreateApiKeyRequest) => createApiKey(data),
    onSuccess: (data) => {
      setCreatedKey(data);
      setNewKeyName("");
      queryClient.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const deleteMut = useMutation({
    mutationFn: deleteApiKey,
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  const handleCopyKey = () => {
    if (createdKey) {
      navigator.clipboard.writeText(createdKey.key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="space-y-3">
      {/* Create new key */}
      <div className="flex gap-2">
        <input
          type="text"
          value={newKeyName}
          onChange={(e) => setNewKeyName(e.target.value)}
          placeholder="New key name..."
          className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm text-white placeholder:text-slate-600 focus:border-accent-500 focus:outline-none"
        />
        <button
          onClick={() => {
            if (newKeyName.trim()) {
              createMut.mutate({ name: newKeyName.trim() });
            }
          }}
          disabled={createMut.isPending || !newKeyName.trim()}
          className="flex items-center gap-2 rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-600 disabled:opacity-60 transition-colors"
        >
          {createMut.isPending ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Plus className="h-3.5 w-3.5" />
          )}
          Create Key
        </button>
      </div>

      {/* Newly created key - shown only once */}
      {createdKey && (
        <div className="rounded-lg border border-emerald-500/30 bg-emerald-500/5 p-4">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm font-medium text-emerald-300">
                API key created: {createdKey.name}
              </p>
              <p className="mt-0.5 text-xs text-emerald-400/70">
                Copy this key now. It will not be shown again.
              </p>
            </div>
            <button
              onClick={() => setCreatedKey(null)}
              className="text-slate-500 hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-2 flex items-center gap-2">
            <code className="flex-1 rounded bg-slate-900 px-3 py-2 font-mono text-sm text-white">
              {createdKey.key}
            </code>
            <button
              onClick={handleCopyKey}
              className="flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-400 hover:text-white transition-colors"
            >
              {copied ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <Copy className="h-4 w-4" />
              )}
              {copied ? "Copied" : "Copy"}
            </button>
          </div>
        </div>
      )}

      {/* Existing keys list */}
      {isLoading ? (
        <div className="py-4 text-center">
          <Loader2 className="inline h-5 w-5 animate-spin text-slate-500" />
        </div>
      ) : !apiKeys || apiKeys.length === 0 ? (
        <p className="py-4 text-center text-sm text-slate-500">
          No API keys created yet.
        </p>
      ) : (
        <div className="space-y-2">
          {apiKeys.map((key) => (
            <div
              key={key.id}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-800/30 px-4 py-2.5"
            >
              <div className="flex items-center gap-3">
                <Key className="h-4 w-4 text-slate-500" />
                <div>
                  <p className="text-sm font-medium text-white">{key.name}</p>
                  <p className="text-xs text-slate-500">
                    {key.key_prefix}... &middot;{" "}
                    {key.last_used_at
                      ? `Last used ${new Date(key.last_used_at).toLocaleDateString()}`
                      : "Never used"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ActiveDot active={key.is_active} />
                <IconButton
                  icon={<Trash2 className="h-3.5 w-3.5" />}
                  onClick={() => {
                    if (confirm(`Delete API key "${key.name}"?`)) {
                      deleteMut.mutate(key.id);
                    }
                  }}
                  label="Delete"
                  variant="danger"
                />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────
// Users Tab (Admin only)
// ────────────────────────────────────────────────────────────────────

function UsersTab() {
  const { user: currentUser } = useAuth();
  const [editItem, setEditItem] = useState<User | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: getUsers,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Manage team members and their roles.
        </p>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 rounded-lg bg-accent-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-accent-600 transition-colors"
        >
          <Plus className="h-3.5 w-3.5" />
          Add User
        </button>
      </div>

      {isLoading ? (
        <SettingsTableSkeleton />
      ) : !users || users.length === 0 ? (
        <EmptyState message="No users found." />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-800">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-850/80">
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Name
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Email
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Role
                </th>
                <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Status
                </th>
                <th className="w-20 px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {users.map((user) => (
                <tr
                  key={user.id}
                  className="transition-colors hover:bg-slate-800/30"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary-600/20 text-xs font-semibold text-primary-200">
                        {user.full_name
                          .split(" ")
                          .map((n) => n[0])
                          .join("")
                          .toUpperCase()
                          .slice(0, 2)}
                      </div>
                      <span className="text-sm font-medium text-white">
                        {user.full_name}
                        {user.id === currentUser?.id && (
                          <span className="ml-1 text-2xs text-slate-500">
                            (you)
                          </span>
                        )}
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-400">
                    {user.email}
                  </td>
                  <td className="px-4 py-3">
                    <RoleBadge role={user.role} />
                  </td>
                  <td className="px-4 py-3">
                    <ActiveDot active={user.is_active} />
                  </td>
                  <td className="px-4 py-3">
                    <IconButton
                      icon={<Pencil className="h-3.5 w-3.5" />}
                      onClick={() => setEditItem(user)}
                      label="Edit"
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showCreate && (
        <CreateUserDialog
          onClose={() => setShowCreate(false)}
        />
      )}
      {editItem && (
        <EditUserDialog
          user={editItem}
          onClose={() => setEditItem(null)}
        />
      )}
    </div>
  );
}

function CreateUserDialog({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("agent");
  const [formError, setFormError] = useState<string | null>(null);

  const createMut = useMutation({
    mutationFn: (data: CreateUserRequest) => createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: () => setFormError("Failed to create user."),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim() || !password.trim()) {
      setFormError("All fields are required.");
      return;
    }
    if (password.length < 8) {
      setFormError("Password must be at least 8 characters.");
      return;
    }
    createMut.mutate({
      full_name: fullName,
      email,
      password,
      role,
    });
  };

  return (
    <DialogShell title="Create User" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {formError && <FormError message={formError} />}
        <FormField label="Full Name" required>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="settings-input"
            placeholder="Jane Smith"
          />
        </FormField>
        <FormField label="Email" required>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="settings-input"
            placeholder="jane@company.com"
          />
        </FormField>
        <FormField label="Password" required>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="settings-input"
            placeholder="At least 8 characters"
          />
        </FormField>
        <FormField label="Role" required>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            className="settings-input"
          >
            <option value="agent">Agent</option>
            <option value="team_lead">Team Lead</option>
            <option value="admin">Admin</option>
          </select>
        </FormField>
        <DialogActions onClose={onClose} isPending={createMut.isPending} isEdit={false} />
      </form>
    </DialogShell>
  );
}

function EditUserDialog({
  user,
  onClose,
}: {
  user: User;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState(user.full_name);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState<UserRole>(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [formError, setFormError] = useState<string | null>(null);

  const updateMut = useMutation({
    mutationFn: (data: UpdateUserRequest) => updateUser(user.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      onClose();
    },
    onError: () => setFormError("Failed to update user."),
  });

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim()) {
      setFormError("Name and email are required.");
      return;
    }
    updateMut.mutate({ full_name: fullName, email, role, is_active: isActive });
  };

  return (
    <DialogShell title={`Edit User: ${user.full_name}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        {formError && <FormError message={formError} />}
        <FormField label="Full Name" required>
          <input
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="settings-input"
          />
        </FormField>
        <FormField label="Email" required>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="settings-input"
          />
        </FormField>
        <FormField label="Role">
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as UserRole)}
            className="settings-input"
          >
            <option value="agent">Agent</option>
            <option value="team_lead">Team Lead</option>
            <option value="admin">Admin</option>
          </select>
        </FormField>
        <label className="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
            className="rounded border-slate-600"
          />
          Active
        </label>
        <DialogActions onClose={onClose} isPending={updateMut.isPending} isEdit={true} />
      </form>
    </DialogShell>
  );
}

// ────────────────────────────────────────────────────────────────────
// Shared reusable UI components
// ────────────────────────────────────────────────────────────────────

function DialogShell({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-lg animate-fade-in rounded-xl border border-slate-800 bg-slate-850 shadow-2xl">
        <div className="flex items-center justify-between border-b border-slate-800 px-6 py-4">
          <h2 className="text-lg font-semibold text-white">{title}</h2>
          <button
            onClick={onClose}
            className="text-slate-500 hover:text-slate-300 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  );
}

function DialogActions({
  onClose,
  isPending,
  isEdit,
}: {
  onClose: () => void;
  isPending: boolean;
  isEdit: boolean;
}) {
  return (
    <div className="flex justify-end gap-2 pt-2">
      <button
        type="button"
        onClick={onClose}
        className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
      >
        Cancel
      </button>
      <button
        type="submit"
        disabled={isPending}
        className="flex items-center gap-2 rounded-lg bg-accent-500 px-4 py-2 text-sm font-medium text-white hover:bg-accent-600 disabled:opacity-60 transition-colors"
      >
        {isPending ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Save className="h-4 w-4" />
        )}
        {isEdit ? "Save Changes" : "Create"}
      </button>
    </div>
  );
}

function FormField({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="mb-1 block text-xs font-medium text-slate-400">
        {label}
        {required && <span className="text-red-400"> *</span>}
      </label>
      {children}
    </div>
  );
}

function FormError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-400">
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
      {message}
    </div>
  );
}

function ActiveDot({ active }: { active: boolean }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          active ? "bg-emerald-400" : "bg-slate-600",
        )}
      />
      <span className="text-xs text-slate-500">
        {active ? "Active" : "Inactive"}
      </span>
    </span>
  );
}

function RoleBadge({ role }: { role: UserRole }) {
  const styles: Record<UserRole, string> = {
    admin: "bg-purple-500/10 text-purple-400 border-purple-500/20",
    team_lead: "bg-blue-500/10 text-blue-400 border-blue-500/20",
    agent: "bg-slate-700/50 text-slate-400 border-slate-600",
  };

  const labels: Record<UserRole, string> = {
    admin: "Admin",
    team_lead: "Team Lead",
    agent: "Agent",
  };

  return (
    <span
      className={cn(
        "inline-flex rounded-full border px-2 py-0.5 text-2xs font-medium",
        styles[role],
      )}
    >
      {labels[role]}
    </span>
  );
}

function IconButton({
  icon,
  onClick,
  label,
  variant = "default",
}: {
  icon: React.ReactNode;
  onClick: () => void;
  label: string;
  variant?: "default" | "danger";
}) {
  return (
    <button
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
      title={label}
      className={cn(
        "rounded-md p-1.5 transition-colors",
        variant === "danger"
          ? "text-slate-600 hover:bg-red-500/10 hover:text-red-400"
          : "text-slate-600 hover:bg-slate-700 hover:text-slate-300",
      )}
    >
      {icon}
    </button>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex items-center justify-center rounded-xl border border-dashed border-slate-700 py-16 text-sm text-slate-500">
      {message}
    </div>
  );
}

function SettingsTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div
          key={i}
          className="h-14 animate-pulse rounded-lg border border-slate-800 bg-slate-850/40"
          style={{ animationDelay: `${i * 60}ms` }}
        />
      ))}
    </div>
  );
}
