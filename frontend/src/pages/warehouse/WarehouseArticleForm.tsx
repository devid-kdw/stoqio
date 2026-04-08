import { useState } from 'react'

import {
  Button,
  Checkbox,
  Group,
  Loader,
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  Text,
  TextInput,
  Textarea,
} from '@mantine/core'

import type {
  ArticleCategoryLookupItem,
  ArticleUomLookupItem,
  SupplierLookupItem,
} from '../../api/articles'
import {
  buildUomMap,
  createArticleSupplierFormItem,
  getQuantityScale,
  getQuantityStep,
  type WarehouseArticleFormErrors,
  type WarehouseArticleSupplierFormItem,
  type WarehouseArticleFormState,
} from './warehouseUtils'

interface WarehouseArticleFormProps {
  form: WarehouseArticleFormState
  errors: WarehouseArticleFormErrors
  categories: ArticleCategoryLookupItem[]
  uoms: ArticleUomLookupItem[]
  supplierOptions: SupplierLookupItem[]
  supplierOptionsLoading?: boolean
  supplierOptionsError?: string | null
  disabled?: boolean
  barcodeActionLabel?: string
  barcodeActionLoading?: boolean
  barcodeActionDisabled?: boolean
  barcodeActionTitle?: string
  onBarcodeAction?: () => void
  onRetrySuppliers?: () => void
  onChange: <K extends keyof WarehouseArticleFormState>(
    field: K,
    value: WarehouseArticleFormState[K]
  ) => void
}

export default function WarehouseArticleForm({
  form,
  errors,
  categories,
  uoms,
  supplierOptions,
  supplierOptionsLoading = false,
  supplierOptionsError = null,
  disabled = false,
  barcodeActionLabel,
  barcodeActionLoading = false,
  barcodeActionDisabled = false,
  barcodeActionTitle,
  onBarcodeAction,
  onRetrySuppliers,
  onChange,
}: WarehouseArticleFormProps) {
  const [supplierSearchQueries, setSupplierSearchQueries] = useState<Record<string, string>>({})

  const uomMap = buildUomMap(uoms)
  const supplierSelectData = supplierOptions.map((supplier) => ({
    value: String(supplier.id),
    label: `${supplier.name} (${supplier.internal_code})`,
  }))

  const addSupplier = () => {
    onChange('suppliers', [...form.suppliers, createArticleSupplierFormItem()])
  }

  const updateSupplier = (
    index: number,
    field: keyof WarehouseArticleSupplierFormItem,
    value: WarehouseArticleSupplierFormItem[typeof field]
  ) => {
    const nextSuppliers = form.suppliers.map((supplier, supplierIndex) =>
      supplierIndex === index
        ? {
            ...supplier,
            [field]: value,
          }
        : supplier
    )
    onChange('suppliers', nextSuppliers)
  }

  const removeSupplier = (key: string) => {
    onChange(
      'suppliers',
      form.suppliers.filter((supplier) => supplier.key !== key)
    )
  }

  return (
    <Stack gap="md">
      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <TextInput
          label="Broj artikla"
          placeholder="ART-001"
          required
          value={form.articleNo}
          onChange={(event) => onChange('articleNo', event.currentTarget.value.toUpperCase())}
          error={errors.articleNo}
          disabled={disabled}
        />

        <Select
          label="Kategorija"
          placeholder="Odaberi kategoriju"
          required
          searchable
          nothingFoundMessage="Nema rezultata."
          data={categories.map((category) => ({
            value: String(category.id),
            label: category.label_hr,
          }))}
          value={form.categoryId}
          onChange={(value) => onChange('categoryId', value)}
          error={errors.categoryId}
          disabled={disabled}
        />

        <Textarea
          label="Opis"
          placeholder="Opis artikla"
          required
          autosize
          minRows={2}
          value={form.description}
          onChange={(event) => onChange('description', event.currentTarget.value)}
          error={errors.description}
          disabled={disabled}
        />

        <Select
          label="Osnovna mjerna jedinica"
          placeholder="Odaberi jedinicu"
          required
          searchable
          nothingFoundMessage="Nema rezultata."
          data={uoms.map((uom) => ({
            value: uom.code,
            label: `${uom.label_hr} (${uom.code})`,
          }))}
          value={form.baseUom}
          onChange={(value) => onChange('baseUom', value)}
          error={errors.baseUom}
          disabled={disabled}
        />

        <NumberInput
          label="Veličina pakiranja"
          placeholder="25"
          value={form.packSize}
          onChange={(value) => onChange('packSize', value)}
          error={errors.packSize}
          min={0}
          step={0.01}
          decimalScale={3}
          disabled={disabled}
        />

        <Select
          label="Jedinica pakiranja"
          placeholder="Odaberi jedinicu"
          searchable
          nothingFoundMessage="Nema rezultata."
          data={uoms.map((uom) => ({
            value: uom.code,
            label: `${uom.label_hr} (${uom.code})`,
          }))}
          value={form.packUom}
          onChange={(value) => onChange('packUom', value)}
          error={errors.packUom}
          disabled={disabled}
        />

        {!form.hasBatch && onBarcodeAction ? (
          <Group align="flex-start" gap="sm" wrap="nowrap">
            <TextInput
              style={{ flex: 1 }}
              label="Barkod"
              placeholder="Opcionalno"
              value={form.barcode}
              onChange={(event) => onChange('barcode', event.currentTarget.value)}
              error={errors.barcode}
              disabled={disabled}
            />
            <Button
              type="button"
              variant="default"
              mt={26}
              onClick={onBarcodeAction}
              loading={barcodeActionLoading}
              disabled={disabled || barcodeActionDisabled}
              title={barcodeActionTitle}
            >
              {barcodeActionLabel ?? 'Generiraj'}
            </Button>
          </Group>
        ) : !form.hasBatch ? (
          <TextInput
            label="Barkod"
            placeholder="Opcionalno"
            value={form.barcode}
            onChange={(event) => onChange('barcode', event.currentTarget.value)}
            error={errors.barcode}
            disabled={disabled}
          />
        ) : null}

        <TextInput
          label="Proizvođač (opcionalno)"
          placeholder="Opcionalno"
          value={form.manufacturer}
          onChange={(event) => onChange('manufacturer', event.currentTarget.value)}
          error={errors.manufacturer}
          disabled={disabled}
        />

        <NumberInput
          label="Prag naručivanja"
          placeholder="10"
          value={form.reorderThreshold}
          onChange={(value) => onChange('reorderThreshold', value)}
          error={errors.reorderThreshold}
          min={0}
          step={getQuantityStep(form.baseUom, uomMap)}
          decimalScale={getQuantityScale(form.baseUom, uomMap)}
          disabled={disabled}
        />

        <NumberInput
          label="Prosječna cijena"
          placeholder="0,0000"
          value={form.initialAveragePrice}
          onChange={(value) => onChange('initialAveragePrice', value)}
          error={errors.initialAveragePrice}
          min={0}
          step={0.01}
          decimalScale={4}
          disabled={disabled}
        />
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <div style={{ width: 'fit-content' }}>
          <Switch
            label="Artikl sa šaržom"
            checked={form.hasBatch}
            onChange={(event) => onChange('hasBatch', event.currentTarget.checked)}
            disabled={disabled}
          />
        </div>

        <div style={{ width: 'fit-content' }}>
          <Switch
            label="Aktivan artikl"
            checked={form.isActive}
            onChange={(event) => onChange('isActive', event.currentTarget.checked)}
            disabled={disabled}
          />
        </div>
      </SimpleGrid>

      <Stack gap="sm">
        <Group justify="space-between" align="flex-start">
          <div>
            <Text fw={600}>Dobavljači</Text>
            <Text size="sm" c="dimmed">
              Poveži dobavljače i njihove šifre artikla po potrebi.
            </Text>
          </div>

          <Button
            type="button"
            variant="light"
            onClick={addSupplier}
            disabled={disabled || supplierOptionsLoading || Boolean(supplierOptionsError)}
          >
            + Dodaj dobavljača
          </Button>
        </Group>

        {errors.suppliers ? (
          <Text size="sm" c="red">
            {errors.suppliers}
          </Text>
        ) : null}

        {supplierOptionsLoading ? (
          <Group gap="xs">
            <Loader size="xs" />
            <Text size="sm" c="dimmed">
              Učitavanje dobavljača…
            </Text>
          </Group>
        ) : null}

        {supplierOptionsError ? (
          <Group justify="space-between" align="center">
            <Text size="sm" c="red">
              {supplierOptionsError}
            </Text>
            {onRetrySuppliers ? (
              <Button type="button" size="xs" variant="default" onClick={onRetrySuppliers}>
                Pokušaj ponovno
              </Button>
            ) : null}
          </Group>
        ) : null}

        {form.suppliers.length === 0 ? (
          <Text size="sm" c="dimmed">
            Nije dodan nijedan dobavljač.
          </Text>
        ) : (
          <Stack gap="md">
            {form.suppliers.map((supplier, index) => (
              <SimpleGrid key={supplier.key} cols={{ base: 1, md: 4 }} spacing="md">
                <Select
                  label="Dobavljač"
                  placeholder="Odaberi dobavljača"
                  searchable
                  clearable
                  data={supplierSelectData}
                  value={supplier.supplierId}
                  onChange={(value) => updateSupplier(index, 'supplierId', value)}
                  onSearchChange={(q) =>
                    setSupplierSearchQueries((prev) => ({ ...prev, [supplier.key]: q }))
                  }
                  nothingFoundMessage={
                    supplierSearchQueries[supplier.key]?.trim() ? 'Nema rezultata.' : undefined
                  }
                  filter={({ options, search }) => {
                    const q = search.trim().toLowerCase()
                    if (!q) return options
                    return options.filter(
                      (opt) => 'value' in opt && opt.label?.toLowerCase().includes(q)
                    )
                  }}
                  maxDropdownHeight={260}
                  error={errors.supplierRows?.[index]?.supplierId}
                  disabled={disabled || supplierOptionsLoading || Boolean(supplierOptionsError)}
                />

                <TextInput
                  label="Šifra artikla kod dobavljača"
                  placeholder="Opcionalno"
                  value={supplier.supplierArticleCode}
                  onChange={(event) =>
                    updateSupplier(index, 'supplierArticleCode', event.currentTarget.value)
                  }
                  error={errors.supplierRows?.[index]?.supplierArticleCode}
                  disabled={disabled}
                />

                <Checkbox
                  mt={30}
                  label="Preferirani dobavljač"
                  checked={supplier.isPreferred}
                  onChange={(event) =>
                    updateSupplier(index, 'isPreferred', event.currentTarget.checked)
                  }
                  disabled={disabled}
                />

                <Button
                  type="button"
                  variant="default"
                  color="red"
                  mt={24}
                  onClick={() => removeSupplier(supplier.key)}
                  disabled={disabled}
                >
                  Ukloni
                </Button>
              </SimpleGrid>
            ))}
          </Stack>
        )}
      </Stack>
    </Stack>
  )
}
