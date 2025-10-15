import pandas as pd

class RepGen:
    def __init__(self,file_name,outputfile_name):
        self.Convert_to_Frame(file_name)
        self.Is_Data_good()

    def Convert_to_Frame(self,file_name):
        self.dfs = pd.read_excel(file_name,header=None)

    def Is_Data_good(self):
        pass
        #print (self.dfs.isnull().values.any())
        #print (self.dfs.isnull().sum())


# Subclass to generate a report of particluar format from excel file
# Here we evaluate specific outputs needed to generate this report.

##-------------------------- REPORT 1 -----------------------------##
class Rev_Exp(RepGen):

    def __init__(self,file_name,outputfile_name):
        super().__init__(file_name,outputfile_name)
        print ('{}'.format(file_name))
        self.df1 = pd.read_excel(file_name,skiprows=4,encoding='utf-8')
        self.Do_Accounting()
        self.Set_Writer(outputfile_name)
        self.Is_Data_good()
        self.Set_Layout()
        self.Save_to_excel()

    def Set_Writer(self,outputfile_name):
        self.writer = pd.ExcelWriter(outputfile_name, engine='xlsxwriter',options={'encoding':'utf-8'})
        self.df1.to_excel(self.writer, index=False, sheet_name='Profit and Loss by Month',startrow=4)
        self.workbook = self.writer.book
        self.worksheet = self.writer.sheets['Profit and Loss by Month']

    def Do_Accounting(self):
        self.df1['Total'] = self.df1[self.df1.columns[1]] + self.df1[self.df1.columns[2]]
        self.df1.rename(columns={self.df1.columns[0] :'Particulars'}, inplace=True)
        self.df1.rename(columns={self.df1.columns[1] :self.df1.columns[1].strftime('%B')}, inplace=True)
        self.df1.rename(columns={self.df1.columns[2] :self.df1.columns[2].strftime('%B')}, inplace=True)

    def Set_Layout(self):
        self.worksheet.hide_gridlines(2)
        fmt= self.workbook.add_format({'num_format': '#,##0.00 _€'})

        self.worksheet.set_column('B:D', 20,fmt)
        self.worksheet.set_column('A:A', 50,fmt)

        merge_cells(self.workbook,self.worksheet,'A1','D1', str(self.dfs.iloc[0,0]))
        merge_cells(self.workbook,self.worksheet,'A2','D2', str(self.dfs.iloc[1,0]))
        merge_cells(self.workbook,self.worksheet,'A3','D3', str(self.dfs.iloc[2,0]))

        lst = self.df1.index[self.df1['Particulars']=='Total Income'][0]
        currency_format = self.workbook.add_format({'num_format': '"₹"* #,##0.00 _€','bold': True})
        self.worksheet.write(14,3, self.df1.iloc[9,3], currency_format)
        self.worksheet.write(14,2, self.df1.iloc[9,2], currency_format)
        self.worksheet.write(14,1, self.df1.iloc[9,1], currency_format)
        self.worksheet.write(14,0, self.df1.iloc[9,0], currency_format)

    def Save_to_excel(self):
        self.writer.save()


#----------------List Of Functions--------------------#
def merge_cells(workbook,worksheet,cell1,cell2,string=None):
    try:
        merge_center = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'font': 13})
        worksheet.merge_range(str(cell1)+':'+str(cell2), string, merge_center)

    except Exception as e:
        print(e)

def hide_gridlines(worksheet,num):
    try:
        worksheet.hide_gridlines(num)
    except Exception as e:
        print(e)

def set_column_width(worksheet,A,B,num):
    try:
        worksheet.set_column(str(A)+':'+str(B), num)
    except Exception as e:
        print(e)

def insert_image(worksheet,A):
    pass

def set_bold(worksheet,A):
    pass

def set_format(worksheet,A):
    pass

def draw_border(worksheet,A):
    pass