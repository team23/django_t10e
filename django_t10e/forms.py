import json
import floppyforms.__future__ as forms


class HiddenSyncedI18nFieldsWidget(forms.HiddenInput):
    def __init__(self, *args, **kwargs):
        self.form = kwargs.pop('form')
        super(HiddenSyncedI18nFieldsWidget, self).__init__(*args, **kwargs)

    def _format_value(self, value):
        value = self.form.map_synced_i18n_model_to_form_fields(value)
        return json.dumps(value)


class SyncedI18NFieldsFormMixin(object):
    def __init__(self, *args, **kwargs):
        super(SyncedI18NFieldsFormMixin, self).__init__(*args, **kwargs)
        if 'unsynced_i18n_fields' in self.fields:
            self.fields['unsynced_i18n_fields'].widget = HiddenSyncedI18nFieldsWidget(form=self)

    def clean_unsynced_i18n_fields(self):
        values = set(self.cleaned_data['unsynced_i18n_fields'])
        # Rip out invalid values.
        possible_values = set(self.get_synced_i18n_fields())
        impossible_values = values.difference(possible_values)
        values = values - impossible_values
        values = self.map_synced_i18n_form_to_model_fields(values)
        return list(values)

    def get_synced_i18n_model_fields(self):
        return self.instance.get_synced_i18n_fields()

    def get_unsynced_i18n_model_fields(self):
        return self.instance.get_unsynced_i18n_fields()

    def get_synced_i18n_model_to_form_fields(self):
        """
        Map model field names to form field names, e.g.:

            return {
                '_media': 'media',
                '_events': None,
            }

        Fields that have ``None`` as value will be not be listed as synced.
        """
        return {}

    def map_synced_i18n_model_to_form_fields(self, fields):
        field_map = self.get_synced_i18n_model_to_form_fields()
        return [
            field_map.get(field) or field
            for field in fields
            if not (field in field_map and field_map[field] is None)]

    def map_synced_i18n_form_to_model_fields(self, fields):
        field_map = self.get_synced_i18n_model_to_form_fields()
        # reverse field map
        field_map = dict(
            (value, key)
            for key, value in field_map.items()
            if value is not None)
        return [
            field_map.get(field) or field
            for field in fields
            if not (field in field_map and field_map[field] is None)]

    def get_to_be_unsynced_i18n_fields(self):
        if hasattr(self, 'cleaned_data') and 'unsynced_i18n_fields' in self.cleaned_data:
            fields = list(self.cleaned_data['unsynced_i18n_fields'])
        else:
            fields = list(self.instance.unsynced_i18n_fields)
        return self.map_synced_i18n_model_to_form_fields(fields)

    def get_synced_i18n_fields(self):
        return self.map_synced_i18n_model_to_form_fields(
            self.get_synced_i18n_model_fields())

    def get_unsynced_i18n_fields(self):
        return self.map_synced_i18n_model_to_form_fields(
            self.get_unsynced_i18n_model_fields())
