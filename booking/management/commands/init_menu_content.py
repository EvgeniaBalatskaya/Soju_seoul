from django.core.management.base import BaseCommand
from booking.models import MenuContent


class Command(BaseCommand):
    help = 'Initialize menu content with default data'

    def handle(self, *args, **options):
        default_content = [
            {
                'section': 'intro',
                'title_kr': '한국 요리의 히트작',
                'title_ru': 'Хиты корейской кухни',
                'content_ru': 'Эти блюда – результат многовековой истории Кореи. От старинных рецептов, передававшихся из поколения в поколение, до традиционных уличных закусок Сеула – каждый рецепт хранит в себе культуру, обычаи и вкусовые предпочтения корейского народа. Попробовав их, вы ощущаете дух истории этой удивительной страны'
            },
            {
                'section': 'kimchi',
                'title_kr': '김치',
                'title_ru': 'Кимчи',
                'content_ru': 'Искусно ферментированная капуста с пикантными специями, раскрывающая богатство корейской кухни в каждом кусочке. Это традиционное корейское блюдо передаёт рецепты и культуру страны на протяжении столетий'
            },
            {
                'section': 'kimbap',
                'title_kr': '김밥',
                'title_ru': 'Кимбап',
                'content_ru': 'Лёгкая и вкусная закуска: рис, свежие овощи, омлет и мясо, завернутые в лист нори. Она отражает культуру простых и питательных блюд, любимых в повседневной жизни корейцев'
            },
            {
                'section': 'tteokbokki',
                'title_kr': '떡볶이',
                'title_ru': 'Токпокки',
                'content_ru': 'Популярные в Корее мягкие рисовые лепёшки в остро-сладком соусе. Это блюдо объединяет гастрономические традиции и современную уличную культуру'
            },
            {
                'section': 'jjajangmyeon',
                'title_kr': '짜장면',
                'title_ru': 'Чаджанмен',
                'content_ru': 'Лапша в тёмном соевом соусе с обжаренным мясом и овощами. Насыщенный вкус и аромат делают это блюдо любимым в Корее и за её пределами'
            },
            {
                'section': 'soju',
                'title_kr': '소주',
                'title_ru': 'Соджу',
                'content_ru': 'Лёгкий и ароматный корейский алкогольный напиток, который идеально дополняет богатый вкус традиционных блюд. В нашем ресторане Soju & Seoul вы можете попробовать оригинальный соджу, подаваемый в сочетании с фирменными закусками и блюдами. Этот напиток олицетворяет атмосферу Сеула и позволяет ощутить корейскую культуру в каждой капле'
            },
            {
                'section': 'footer',
                'title_kr': '',
                'title_ru': '',
                'content_ru': 'В Soju & Seoul каждая закуска — это маленькое путешествие в сердце Кореи. От хрустящих овощных блинчиков до пикантного кимчи и нежного кimbap — наши закуски готовятся по традиционным рецептам, с любовью к вкусу и свежести ингредиентов. Они идеально дополняют основные блюда и напитки, создавая полный гастрономический опыт настоящей корейской кухни'
            },
        ]

        for item in default_content:
            # Получаем или создаем объект
            obj, created = MenuContent.objects.get_or_create(
                section=item['section']
            )

            # Обновляем поля независимо от того, создан он или уже существовал
            obj.title_kr = item['title_kr']
            obj.title_ru = item['title_ru']
            obj.content_ru = item['content_ru']
            obj.save()

            if created:
                self.stdout.write(self.style.SUCCESS(f"✓ Created {item['section']}"))
            else:
                self.stdout.write(self.style.WARNING(f"↻ Updated {item['section']}"))

        self.stdout.write(self.style.SUCCESS('✓ Successfully initialized all menu content'))
