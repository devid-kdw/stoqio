import {
  NumberInput,
  Select,
  SimpleGrid,
  Stack,
  Switch,
  TextInput,
  Textarea,
} from '@mantine/core'

import type {
  ArticleCategoryLookupItem,
  ArticleUomLookupItem,
} from '../../api/articles'
import {
  buildUomMap,
  getQuantityScale,
  getQuantityStep,
  type WarehouseArticleFormErrors,
  type WarehouseArticleFormState,
} from './warehouseUtils'

interface WarehouseArticleFormProps {
  form: WarehouseArticleFormState
  errors: WarehouseArticleFormErrors
  categories: ArticleCategoryLookupItem[]
  uoms: ArticleUomLookupItem[]
  disabled?: boolean
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
  disabled = false,
  onChange,
}: WarehouseArticleFormProps) {
  const uomMap = buildUomMap(uoms)

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

        <TextInput
          label="Barkod"
          placeholder="Opcionalno"
          value={form.barcode}
          onChange={(event) => onChange('barcode', event.currentTarget.value)}
          error={errors.barcode}
          disabled={disabled}
        />

        <TextInput
          label="Proizvođač"
          placeholder="Opcionalno"
          value={form.manufacturer}
          onChange={(event) => onChange('manufacturer', event.currentTarget.value)}
          error={errors.manufacturer}
          disabled={disabled}
        />

        <TextInput
          label="Šifra proizvođača"
          placeholder="Opcionalno"
          value={form.manufacturerArtNumber}
          onChange={(event) => onChange('manufacturerArtNumber', event.currentTarget.value)}
          error={errors.manufacturerArtNumber}
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
      </SimpleGrid>

      <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
        <Switch
          label="Artikl sa šaržom"
          checked={form.hasBatch}
          onChange={(event) => onChange('hasBatch', event.currentTarget.checked)}
          disabled={disabled}
        />

        <Switch
          label="Aktivan artikl"
          checked={form.isActive}
          onChange={(event) => onChange('isActive', event.currentTarget.checked)}
          disabled={disabled}
        />
      </SimpleGrid>
    </Stack>
  )
}
