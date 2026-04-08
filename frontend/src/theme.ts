import { createTheme, Table } from '@mantine/core'

export const stoqioTheme = createTheme({
  components: {
    Table: Table.extend({
      defaultProps: {
        striped: 'odd',
      },
    }),
  },
})
