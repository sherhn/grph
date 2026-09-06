using System;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace WindowsFormsApp1
{
    public partial class Form1 : Form
    {
        public Form1()
        {
            InitializeComponent();
        }

        string filePath = string.Empty;
        string fileName = string.Empty;

        private void button1_Click(object sender, EventArgs e)
        {
            if (openFileDialog1.ShowDialog() == DialogResult.Cancel)
            {
                return;
            }

            filePath = openFileDialog1.FileName;
            fileName = Path.GetFileName(filePath);

            label1.Text = "Файл: " + fileName;
        }

        private void button2_Click(object sender, EventArgs e)
        {
            if (filePath != string.Empty)
            {
                Bitmap bitmap = new Bitmap(filePath);

                int width = bitmap.Width - 1;
                int height = bitmap.Height - 1;

                Color firstColor = Color.FromArgb(64, 64, 127);
                Color secondColor = Color.FromArgb(127, 64, 127);
                Color thirthColor = Color.FromArgb(127, 127, 64);

                bitmap.SetPixel(0, 0, firstColor);
                bitmap.SetPixel(width, 0, secondColor);
                bitmap.SetPixel(width, height, thirthColor);

                saveFileDialog1.FileName = fileName + " - result";
                saveFileDialog1.Filter = "Изображения PNG|*.png|Изображения JPG|*.jpg|Все файлы|*.*";
                saveFileDialog1.FilterIndex = 1;

                if (saveFileDialog1.ShowDialog() == DialogResult.Cancel)
                {
                    return;
                }

                bitmap.Save(saveFileDialog1.FileName);

                bitmap.Dispose();

                label1.Text = "Файл сохранен!";

                filePath = string.Empty;
                fileName = string.Empty;
            }
        }
    }
}
